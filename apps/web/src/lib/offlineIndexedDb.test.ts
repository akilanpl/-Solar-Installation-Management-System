import { IDBFactory, IDBObjectStore as FakeStore } from "fake-indexeddb";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createIndexedDbStore, OFFLINE_SCHEMA_VERSION, type QueuedOperation } from "./offlineQueue";

beforeEach(() => vi.stubGlobal("indexedDB", new IDBFactory()));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
function operation(userId: string, id = "same-operation"): QueuedOperation {
  return {user_id:userId,client_operation_id:id,op_type:"survey_draft",entity_type:"survey",entity_id:"survey-1",base_field_version:0,payload:{notes:"Saved roof measurements"},state:"queued",attempts:2,error:null,updated_at:"2026-11-01T00:00:00Z",schema_version:OFFLINE_SCHEMA_VERSION};
}
function openDb(name: string, version: number, seed?: QueuedOperation[]): Promise<IDBDatabase> {
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open(name,version);
    request.onupgradeneeded=()=>{
      const store=request.result.createObjectStore("ops",{keyPath:"client_operation_id"});
      store.createIndex("by_user","user_id");
      for(const row of seed??[]) store.put(row);
    };
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error);
  });
}
function read<T>(db: IDBDatabase, store: string, key: IDBValidKey): Promise<T> {
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(store,"readonly"); const request=tx.objectStore(store).get(key);
    let value:T; request.onsuccess=()=>{value=request.result;};
    tx.oncomplete=()=>resolve(value);tx.onabort=()=>reject(tx.error);
  });
}

it("resolves a draft write only after the actual transaction commits",async()=>{
  const events:string[]=[];const original=FakeStore.prototype.put;
  vi.spyOn(FakeStore.prototype,"put").mockImplementation(function(this:FakeStore,...args:Parameters<typeof original>){
    const request=original.apply(this,args);
    request.addEventListener("success",()=>events.push("request-success"));
    this.transaction.addEventListener("complete",()=>events.push("commit"));
    return request;
  });
  const store=createIndexedDbStore("commit-order");
  await store.put(operation("tech-a")).then(()=>events.push("resolved"));
  expect(events).toEqual(["request-success","commit","resolved"]);
  expect((await store.list("tech-a"))[0].payload.notes).toBe("Saved roof measurements");
});

it("rejects an abort after request success without claiming a saved draft",async()=>{
  const original=FakeStore.prototype.put;
  vi.spyOn(FakeStore.prototype,"put").mockImplementation(function(this:FakeStore,...args:Parameters<typeof original>){
    const request=original.apply(this,args);
    request.addEventListener("success",()=>this.transaction.abort());
    return request;
  });
  const store=createIndexedDbStore("aborted-write");
  await expect(store.put(operation("tech-a"))).rejects.toThrow(/abort/i);
  expect(await store.list("tech-a")).toEqual([]);
});

it("keeps reused operation IDs separate across accounts",async()=>{
  const store=createIndexedDbStore("account-isolation");
  await store.put(operation("tech-a")); await store.put(operation("tech-b"));
  expect((await store.list("tech-a")).map(row=>row.user_id)).toEqual(["tech-a"]);
  expect((await store.list("tech-b")).map(row=>row.user_id)).toEqual(["tech-b"]);
  await store.remove("tech-a","same-operation");
  expect(await store.list("tech-a")).toEqual([]);
  expect(await store.list("tech-b")).toHaveLength(1);
});

it("purges only the requested account in one committed transaction",async()=>{
  const store=createIndexedDbStore("account-purge");
  await store.put(operation("tech-a","one"));await store.put(operation("tech-a","two"));await store.put(operation("tech-b","one"));
  await store.clearUser("tech-a");
  expect(await store.list("tech-a")).toEqual([]);
  expect((await store.list("tech-b"))[0].client_operation_id).toBe("one");
});

it("copies version-one drafts atomically and keeps original recovery records",async()=>{
  const old={...operation("tech-a"),schema_version:1,state:"conflict" as const,attempts:7,error:"Review changed survey"};
  const legacy=await openDb("legacy-drafts",1,[old]);legacy.close();
  const store=createIndexedDbStore("legacy-drafts");
  const migrated=await store.list("tech-a");
  expect(migrated).toEqual([{...old,schema_version:2}]);
  await store.put(operation("tech-b"));
  expect(await store.list("tech-a")).toHaveLength(1);
  expect(await store.list("tech-b")).toHaveLength(1);
  const upgraded=await openDb("legacy-drafts",2);
  expect(upgraded.objectStoreNames.contains("ops")).toBe(true);
  expect(await read(upgraded,"ops",old.client_operation_id)).toEqual(old);
  upgraded.close();
});

it("leaves the legacy database intact if a record cannot be safely migrated",async()=>{
  const invalid={...operation(""),schema_version:1};
  const legacy=await openDb("invalid-legacy",1,[invalid]);legacy.close();
  await expect(createIndexedDbStore("invalid-legacy").list("tech-a")).rejects.toBeDefined();
  const recovered=await openDb("invalid-legacy",1);
  expect(recovered.version).toBe(1);
  expect(recovered.objectStoreNames.contains("ops_by_user_v2")).toBe(false);
  expect(await read(recovered,"ops",invalid.client_operation_id)).toEqual(invalid);
  recovered.close();
});

it("rejects incomplete account identity before storing data",async()=>{
  const store=createIndexedDbStore("invalid-owner");
  await expect(store.put(operation(""))).rejects.toThrow(/identity/);
  expect(await store.list("")).toEqual([]);
});

it("reports aborted purge and retains every affected draft",async()=>{
  const store=createIndexedDbStore("abort-purge");
  await store.put(operation("tech-a","one"));await store.put(operation("tech-a","two"));await store.put(operation("tech-b","one"));
  const original=FakeStore.prototype.delete;
  vi.spyOn(FakeStore.prototype,"delete").mockImplementation(function(this:FakeStore,...args:Parameters<typeof original>){
    const request=original.apply(this,args);
    request.addEventListener("success",()=>this.transaction.abort());
    return request;
  });
  await expect(store.clearUser("tech-a")).rejects.toBeDefined();
  expect(await store.list("tech-a")).toHaveLength(2);
  expect(await store.list("tech-b")).toHaveLength(1);
});
