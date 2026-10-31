export const OFFLINE_ENABLED =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_SOLAROPS_OFFLINE === "on";

export const OFFLINE_SCHEMA_VERSION = 1;
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
  function open(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(dbName, OFFLINE_SCHEMA_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("ops")) {
          const store = db.createObjectStore("ops", { keyPath: "client_operation_id" });
          store.createIndex("by_user", "user_id", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error ?? new Error("IndexedDB unavailable."));
    });
  }

  async function withStore<T>(
    mode: IDBTransactionMode,
    run: (store: IDBObjectStore) => IDBRequest<T>,
  ): Promise<T> {
    const db = await open();
    try {
      return await new Promise<T>((resolve, reject) => {
        const tx = db.transaction("ops", mode);
        const request = run(tx.objectStore("ops"));
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error ?? new Error("IndexedDB write failed."));
      });
    } finally {
      db.close();
    }
  }

  return {
    async list(userId) {
      const db = await open();
      try {
        return await new Promise<QueuedOperation[]>((resolve, reject) => {
          const tx = db.transaction("ops", "readonly");
          const index = tx.objectStore("ops").index("by_user");
          const request = index.getAll(userId);
          request.onsuccess = () => resolve((request.result ?? []) as QueuedOperation[]);
          request.onerror = () => reject(request.error ?? new Error("IndexedDB read failed."));
        });
      } finally {
        db.close();
      }
    },
    async put(record) {
      await withStore("readwrite", (store) => store.put(record));
    },
    async remove(userId, clientOperationId) {
      const rows = await this.list(userId);
      if (!rows.some((row) => row.client_operation_id === clientOperationId)) return;
      await withStore("readwrite", (store) => store.delete(clientOperationId));
    },
    async clearUser(userId) {
      const rows = await this.list(userId);
      const db = await open();
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction("ops", "readwrite");
          const store = tx.objectStore("ops");
          for (const row of rows) store.delete(row.client_operation_id);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error ?? new Error("IndexedDB purge failed."));
        });
      } finally {
        db.close();
      }
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
