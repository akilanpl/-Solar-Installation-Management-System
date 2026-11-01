export const OFFLINE_ENABLED =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_SOLAROPS_OFFLINE === "on";

export const OFFLINE_SCHEMA_VERSION = 2;
export const OFFLINE_MAX_ATTEMPTS = 8;

export type SyncState =
  | "draft"
  | "queued"
  | "syncing"
  | "synced"
  | "conflict"
  | "failed"
  | "auth_required";

export interface QueuedOperation {
  client_operation_id: string;
  user_id: string;
  op_type: string;
  entity_type: string;
  entity_id: string | null;
  base_field_version: number | null;
  payload: Record<string, unknown>;
  state: SyncState;
  attempts: number;
  error: string | null;
  updated_at: string;
  schema_version: number;
}

export interface QueueStore {
  list(userId: string): Promise<QueuedOperation[]>;
  put(record: QueuedOperation): Promise<void>;
  remove(userId: string, clientOperationId: string): Promise<void>;
  clearUser(userId: string): Promise<void>;
}

export function createMemoryStore(): QueueStore {
  const rows = new Map<string, QueuedOperation>();
  const key = (userId: string, id: string) => `${userId}::${id}`;
  return {
    async list(userId) {
      return [...rows.values()]
        .filter((row) => row.user_id === userId)
        .sort((a, b) => a.updated_at.localeCompare(b.updated_at));
    },
    async put(record) {
      rows.set(key(record.user_id, record.client_operation_id), record);
    },
    async remove(userId, clientOperationId) {
      rows.delete(key(userId, clientOperationId));
    },
    async clearUser(userId) {
      for (const mapKey of [...rows.keys()]) {
        if (mapKey.startsWith(`${userId}::`)) rows.delete(mapKey);
      }
    },
  };
}

export function createIndexedDbStore(dbName = "solarops-offline"): QueueStore {
  const activeStore = "ops_by_user_v2";
  function open(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      let blocked = false;
      const request = indexedDB.open(dbName, OFFLINE_SCHEMA_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        const tx = request.transaction!;
        const store = db.createObjectStore(activeStore, {
          keyPath: ["user_id", "client_operation_id"],
        });
        store.createIndex("by_user", "user_id", { unique: false });
        if (db.objectStoreNames.contains("ops")) {
          // Copy within the version-change transaction. Keep the original
          // store for recovery; active reads/writes use only the scoped store.
          const cursor = tx.objectStore("ops").openCursor();
          cursor.onsuccess = () => {
            const item = cursor.result;
            if (!item) return;
            const row = item.value as QueuedOperation;
            if (typeof row.user_id !== "string" || !row.user_id ||
                typeof row.client_operation_id !== "string" || !row.client_operation_id) {
              tx.abort();
              return;
            }
            store.add({ ...row, schema_version: OFFLINE_SCHEMA_VERSION });
            item.continue();
          };
        }
      };
      request.onsuccess = () => {
        const db = request.result;
        db.onversionchange = () => db.close();
        if (blocked) db.close();
        else resolve(db);
      };
      request.onerror = () => reject(request.error ?? new Error("IndexedDB unavailable."));
      request.onblocked = () => {
        blocked = true;
        reject(new Error("Close other SolarOps tabs before upgrading offline drafts."));
      };
    });
  }

  async function withStore<T>(
    mode: IDBTransactionMode,
    run: (store: IDBObjectStore) => IDBRequest<T>,
  ): Promise<T> {
    const db = await open();
    try {
      return await new Promise<T>((resolve, reject) => {
        const tx = db.transaction(activeStore, mode);
        let result: T;
        const request = run(tx.objectStore(activeStore));
        request.onsuccess = () => { result = request.result; };
        // A successful request can still be rolled back by a later abort.
        // Report a saved draft only after the complete transaction commits.
        tx.oncomplete = () => resolve(result);
        tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted."));
        tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed."));
      });
    } finally {
      db.close();
    }
  }

  return {
    async list(userId) {
      const rows = await withStore<QueuedOperation[]>("readonly", store =>
        store.index("by_user").getAll(userId));
      return rows.sort((a, b) => a.updated_at.localeCompare(b.updated_at));
    },
    async put(record) {
      if (!record.user_id || !record.client_operation_id) {
        throw new Error("Offline operation needs its account and operation identity.");
      }
      await withStore("readwrite", store => store.put(record));
    },
    async remove(userId, clientOperationId) {
      await withStore("readwrite", store => store.delete([userId, clientOperationId]));
    },
    async clearUser(userId) {
      await withStore("readwrite", store => {
        const request = store.index("by_user").getAllKeys(userId);
        request.addEventListener("success", () => {
          for (const key of request.result) store.delete(key);
        });
        return request;
      });
    },
  };
}

export function newOperationId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return `op-${[...bytes].map((b) => b.toString(16).padStart(2, "0")).join("")}`;
}

export interface SyncTransport {
  postBatch(
    operations: {
      op_type: string;
      entity_type: string;
      entity_id: string | null;
      client_operation_id: string;
      base_field_version: number | null;
      payload: Record<string, unknown>;
    }[],
  ): Promise<{ verdicts: { client_operation_id: string; status: string; result?: unknown; error?: { message?: string; code?: string } }[] }>;
}

export class OfflineQueue {
  constructor(
    private readonly store: QueueStore,
    private readonly transport: SyncTransport,
    private readonly userId: string,
  ) {}

  async enqueue(entry: {
    op_type: string;
    entity_type: string;
    entity_id: string | null;
    base_field_version: number | null;
    payload: Record<string, unknown>;
    client_operation_id?: string;
  }): Promise<QueuedOperation> {
    const record: QueuedOperation = {
      client_operation_id: entry.client_operation_id ?? newOperationId(),
      user_id: this.userId,
      op_type: entry.op_type,
      entity_type: entry.entity_type,
      entity_id: entry.entity_id,
      base_field_version: entry.base_field_version,
      payload: entry.payload,
      state: "queued",
      attempts: 0,
      error: null,
      updated_at: new Date().toISOString(),
      schema_version: OFFLINE_SCHEMA_VERSION,
    };
    await this.store.put(record);
    return record;
  }

  async saveDraft(
    entry: Parameters<OfflineQueue["enqueue"]>[0],
  ): Promise<QueuedOperation> {
    const record = await this.enqueue(entry);
    record.state = "draft";
    await this.store.put(record);
    return record;
  }

  async list(): Promise<QueuedOperation[]> {
    return this.store.list(this.userId);
  }

  async discard(clientOperationId: string): Promise<void> {
    await this.store.remove(this.userId, clientOperationId);
  }

  async purgeUser(): Promise<void> {
    await this.store.clearUser(this.userId);
  }

  async syncPending(): Promise<QueuedOperation[]> {
    const pending = (await this.store.list(this.userId)).filter(
      (row) => row.state === "queued" || row.state === "failed" || row.state === "auth_required",
    );
    if (pending.length === 0) return [];
    for (const row of pending) {
      row.state = "syncing";
      row.attempts += 1;
      await this.store.put(row);
    }
    let verdicts: Awaited<ReturnType<SyncTransport["postBatch"]>>["verdicts"];
    try {
      const response = await this.transport.postBatch(
        pending.map((row) => ({
          op_type: row.op_type,
          entity_type: row.entity_type,
          entity_id: row.entity_id,
          client_operation_id: row.client_operation_id,
          base_field_version: row.base_field_version,
          payload: row.payload,
        })),
      );
      verdicts = response.verdicts;
    } catch (caught) {
      const authFailure =
        typeof caught === "object" && caught !== null && "status" in caught &&
        (caught as { status: number }).status === 401;
      for (const row of pending) {
        row.state = authFailure ? "auth_required" : "failed";
        row.error = authFailure ? "Sign in again to sync." : "Sync failed before reaching the server.";
        row.updated_at = new Date().toISOString();
        await this.store.put(row);
      }
      return this.store.list(this.userId);
    }
    const byId = new Map(verdicts.map((verdict) => [verdict.client_operation_id, verdict]));
    for (const row of pending) {
      const verdict = byId.get(row.client_operation_id);
      if (!verdict) {
        row.state = row.attempts >= OFFLINE_MAX_ATTEMPTS ? "failed" : "queued";
        row.error = "No server verdict. Will retry.";
      } else if (verdict.status === "applied") {
        row.state = "synced";
        row.error = null;
      } else if (verdict.status === "conflict") {
        row.state = "conflict";
        row.error = "The server record changed. Review and rebase.";
      } else {
        row.state = "failed";
        row.error = verdict.error?.message ?? "The server rejected this change.";
      }
      row.updated_at = new Date().toISOString();
      await this.store.put(row);
    }
    return this.store.list(this.userId);
  }
}
