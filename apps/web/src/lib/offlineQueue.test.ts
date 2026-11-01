import { describe, expect, it, vi } from "vitest";

import {
  OfflineQueue,
  createMemoryStore,
  type QueuedOperation,
  type SyncTransport,
} from "./offlineQueue";

function transportFor(
  verdicts: { client_operation_id: string; status: string; error?: { message: string } }[],
): SyncTransport {
  return { postBatch: vi.fn(async () => ({ verdicts })) };
}

const ENTRY = {
  op_type: "survey_draft",
  entity_type: "survey",
  entity_id: "11111111-1111-1111-1111-111111111111",
  base_field_version: 0,
  payload: { notes: "North roof shaded after 3pm." },
};

describe("OfflineQueue", () => {
  it("marks operations synced when the server applies them", async () => {
    const queue = new OfflineQueue(
      createMemoryStore(),
      transportFor([{ client_operation_id: "op-1", status: "applied" }]),
      "tech-1",
    );
    await queue.enqueue({ ...ENTRY, client_operation_id: "op-1" });
    const rows = await queue.syncPending();
    expect(rows).toHaveLength(1);
    expect(rows[0].state).toBe("synced");
    expect(rows[0].error).toBeNull();
  });

  it("surfaces conflicts for rebasing instead of claiming success", async () => {
    const queue = new OfflineQueue(
      createMemoryStore(),
      transportFor([{ client_operation_id: "op-2", status: "conflict" }]),
      "tech-1",
    );
    await queue.enqueue({ ...ENTRY, client_operation_id: "op-2" });
    const rows = await queue.syncPending();
    expect(rows[0].state).toBe("conflict");
    expect(rows[0].error).toMatch(/rebase/i);
  });

  it("keeps rejected operations as failed with the server reason", async () => {
    const queue = new OfflineQueue(
      createMemoryStore(),
      transportFor([
        {
          client_operation_id: "op-3",
          status: "rejected",
          error: { message: "Too late." },
        },
      ]),
      "tech-1",
    );
    await queue.enqueue({ ...ENTRY, client_operation_id: "op-3" });
    const rows = await queue.syncPending();
    expect(rows[0].state).toBe("failed");
    expect(rows[0].error).toBe("Too late.");
  });

  it("marks auth_required on 401 so the UI asks for sign-in", async () => {
    const failing: SyncTransport = {
      postBatch: async () => {
        throw { status: 401 };
      },
    };
    const queue = new OfflineQueue(createMemoryStore(), failing, "tech-1");
    await queue.enqueue({ ...ENTRY, client_operation_id: "op-4" });
    const rows = await queue.syncPending();
    expect(rows[0].state).toBe("auth_required");
  });

  it("isolates users and purges one account without touching another", async () => {
    const store = createMemoryStore();
    const ok: SyncTransport = { postBatch: async () => ({ verdicts: [] }) };
    const first = new OfflineQueue(store, ok, "tech-1");
    const second = new OfflineQueue(store, ok, "tech-2");
    await first.enqueue({ ...ENTRY, client_operation_id: "op-a" });
    await second.enqueue({ ...ENTRY, client_operation_id: "op-b" });
    expect(await first.list()).toHaveLength(1);
    await first.purgeUser();
    expect(await first.list()).toHaveLength(0);
    expect(await second.list()).toHaveLength(1);
  });

  it("supports drafts that stay local until queued", async () => {
    const seen: QueuedOperation[][] = [];
    const store = createMemoryStore();
    const recording: SyncTransport = {
      postBatch: async () => {
        seen.push(await store.list("tech-1"));
        return { verdicts: [] };
      },
    };
    const queue = new OfflineQueue(store, recording, "tech-1");
    await queue.saveDraft({ ...ENTRY, client_operation_id: "op-d" });
    const rows = await queue.syncPending();
    expect(rows).toHaveLength(0);
    expect(await queue.list()).toHaveLength(1);
    expect((await queue.list())[0].state).toBe("draft");
    expect(seen).toHaveLength(0);
  });
});
