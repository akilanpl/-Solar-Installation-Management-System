"use client";
import { useRef,useState } from "react";
import { api } from "@/lib/api";
export async function post(path:string,body:unknown,key?:string) { return api(path,{method:"POST", ...(body===undefined?{}:{body:JSON.stringify(body)}),headers:key?{"Idempotency-Key":key}:{}}); }
export function WorkflowForm({title,submit,onSaved,children,label="Save"}:{title:string;submit:(data:FormData,key:string)=>Promise<unknown>;onSaved:()=>void;children:React.ReactNode;label?:string}) {
 const [pending,setPending]=useState(false);const [error,setError]=useState<string|null>(null);const [notice,setNotice]=useState(false);const key=useRef<string|null>(null);
 return <form className="actual-workflow-form" onSubmit={async e=>{e.preventDefault();const form=e.currentTarget;setPending(true);setError(null);setNotice(false);try{key.current??=crypto.randomUUID();await submit(new FormData(form),key.current);key.current=null;setNotice(true);form.reset();onSaved();}catch(error){setError(error instanceof Error?error.message:"Could not save. Please retry.");}finally{setPending(false);}}}><h3>{title}</h3><fieldset disabled={pending}><div className="actual-fields">{children}</div><button className="primary-board-btn" type="submit">{pending?"Saving…":label}</button></fieldset>{error&&<p role="alert" className="auth-error-note">{error}</p>}{notice&&<p role="status" className="actual-saved">Saved to your company records.</p>}</form>;
}
export function Input({label,name,type="text",required=true,...props}:{label:string;name:string}&React.ComponentProps<"input">) {return <label className="actual-field"><span>{label}</span><input name={name} type={type} required={required} {...props}/></label>;}
export function Select({label,name,children,required=true}:{label:string;name:string;children:React.ReactNode;required?:boolean}) {return <label className="actual-field"><span>{label}</span><select name={name} required={required} defaultValue=""><option value="" disabled>Choose…</option>{children}</select></label>;}
export function RecordActions({actions,onSaved}:{actions:{label:string;path:string;body?:unknown}[];onSaved:()=>void}) {
 const [pending,setPending]=useState(false);const [error,setError]=useState<string|null>(null);
 return <div className="actual-record-actions">{actions.map(a=><button key={a.label} className="add-assignment-btn" type="button" disabled={pending} onClick={async()=>{setPending(true);setError(null);try{await post(a.path,a.body);onSaved();}catch(e){setError(e instanceof Error?e.message:"Could not save.");}finally{setPending(false);}}}>{a.label}</button>)}{error&&<p role="alert" className="auth-error-note">{error}</p>}</div>;
}
export function value(data:FormData,key:string){return String(data.get(key)??"").trim();}
