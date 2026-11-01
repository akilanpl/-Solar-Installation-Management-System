"use client";
import { useEffect, useRef, useState } from "react";
import { ModalFrame } from "./shell-panels";
import { Accessibility, Volume2, Square, X, Eye, Type, Sparkles, Mic } from "lucide-react";
type Preferences={contrast:boolean;large:boolean;spacing:boolean;motion:boolean};
const DEFAULTS:Preferences={contrast:false,large:false,spacing:false,motion:false};
type RecognitionResult = { isFinal: boolean; 0?: { transcript: string } };
type RecognitionEvent = { resultIndex: number; results: ArrayLike<RecognitionResult> };
type DraftRecognition = {
 lang: string; continuous: boolean; interimResults: boolean;
 onresult: ((event: RecognitionEvent) => void) | null;
 onerror: ((event: { error: string }) => void) | null;
 onend: (() => void) | null;
 start(): void; abort(): void;
};
type RecognitionConstructor = new () => DraftRecognition;
export function finalDictationText(event: RecognitionEvent): string {
 const words: string[] = [];
 for (let i=event.resultIndex;i<event.results.length;i++) {
  const result=event.results[i];
  if(result.isFinal && result[0]?.transcript.trim()) words.push(result[0].transcript.trim());
 }
 return words.join(" ");
}
export function dictationFailure(error: string): string {
 if(error === "not-allowed" || error === "service-not-allowed") return "Microphone or speech service permission was denied. You can type the draft instead.";
 if(error === "no-speech") return "No speech was detected. Your existing draft is unchanged.";
 if(error === "audio-capture") return "No microphone is available. You can type the draft instead.";
 return "Speech recognition is unavailable or interrupted. Your existing draft is unchanged.";
}

export function CustomerAccessibility(){
 const [open,setOpen]=useState(false),[preferences,setPreferences]=useState(DEFAULTS),[ready,setReady]=useState(false),[message,setMessage]=useState("");
 const trigger=useRef<HTMLButtonElement>(null),panel=useRef<HTMLDivElement>(null);
 const recognition=useRef<DraftRecognition|null>(null),[listening,setListening]=useState(false),[transcript,setTranscript]=useState("");
 function stopDictation(){const current=recognition.current;recognition.current=null;if(current){current.onresult=null;current.onerror=null;current.onend=null;current.abort();}setListening(false);}
 useEffect(()=>{if(open)return;const current=recognition.current;recognition.current=null;if(current){current.onresult=null;current.onerror=null;current.onend=null;current.abort();}setListening(false);},[open]);
 useEffect(()=>()=>{const current=recognition.current;recognition.current=null;if(current){current.onresult=null;current.onerror=null;current.onend=null;current.abort();}},[]);
 function startDictation(){
  if(recognition.current)return;
  const browser=window as Window & { SpeechRecognition?:RecognitionConstructor; webkitSpeechRecognition?:RecognitionConstructor };
  const Factory=browser.SpeechRecognition??browser.webkitSpeechRecognition;
  if(!Factory){setMessage("Speech-to-text is not supported in this browser. You can type your draft below.");return;}
  let session:DraftRecognition;try{session=new Factory();}catch{setMessage("Speech recognition is unavailable in this browser context. You can type your draft below.");return;}recognition.current=session;session.lang=document.documentElement.lang||"en";session.continuous=true;session.interimResults=false;
  session.onresult=event=>{if(recognition.current!==session)return;const text=finalDictationText(event);if(text)setTranscript(previous=>[previous.trim(),text].filter(Boolean).join(" "));};
  session.onerror=event=>{if(recognition.current!==session)return;setMessage(dictationFailure(event.error));stopDictation();};
  session.onend=()=>{if(recognition.current===session){recognition.current=null;setListening(false);}};
  try{session.start();setListening(true);setMessage("Listening for your draft. Nothing is submitted or saved to your account.");}catch{stopDictation();setMessage("Speech recognition could not start. You can type the draft instead.");}
 }

 useEffect(()=>{try{const saved=JSON.parse(localStorage.getItem("solarops_customer_accessibility")??"{}");setPreferences({contrast:saved.contrast===true,large:saved.large===true,spacing:saved.spacing===true,motion:saved.motion===true});}catch{}setReady(true);},[]);
 useEffect(()=>{if(!ready)return;const root=document.documentElement;const previous=root.getAttribute("data-customer-accessibility");root.setAttribute("data-customer-accessibility",Object.entries(preferences).filter(([,v])=>v).map(([k])=>k).join(" "));try{localStorage.setItem("solarops_customer_accessibility",JSON.stringify(preferences));}catch{}return()=>{if(previous===null)root.removeAttribute("data-customer-accessibility");else root.setAttribute("data-customer-accessibility",previous);};},[preferences,ready]);
 useEffect(()=>()=>{if("speechSynthesis" in window)window.speechSynthesis.cancel();},[]);
 useEffect(()=>{if(!open)return;const opener=trigger.current;panel.current?.querySelector<HTMLButtonElement>("button")?.focus();return()=>{opener?.focus();};},[open]);
 function readPage(){if(!("speechSynthesis" in window)){setMessage("Read aloud is not supported in this browser.");return;}window.speechSynthesis.cancel();const page=document.querySelector("main .customer-recovery");const text=page instanceof HTMLElement?page.innerText:"";if(!text.trim()){setMessage("There is no visible dashboard content to read yet.");return;}const utterance=new SpeechSynthesisUtterance(text);utterance.rate=.92;window.speechSynthesis.speak(utterance);setMessage("Reading the visible dashboard. No microphone is used.");}
 return <aside className="customer-a11y-floating-trigger" aria-label="Customer Accessibility Assistant"><button ref={trigger} type="button" className={`a11y-pill-btn ${open?"active":""}`} aria-expanded={open} aria-controls="customer-a11y-panel" onClick={()=>setOpen(!open)}><span className="a11y-btn-icon-wrap"><Accessibility size={20}/></span><span className="a11y-btn-label">Accessibility</span></button>{open&&<ModalFrame onClose={()=>setOpen(false)} label="Customer Accessibility Controls" className="customer-a11y-drawer recovery-a11y-dialog"><div ref={panel} id="customer-a11y-panel" onKeyDown={e=>{if(e.key==="Escape")setOpen(false);if(e.key==="Tab"){const controls=Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input,select,textarea')??[]),first=controls[0],last=controls[controls.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}}}><div className="a11y-drawer-header"><div className="a11y-header-title"><Accessibility size={18}/><span>Customer Accessibility Assistant</span></div><button type="button" className="a11y-close-btn" aria-label="Close Accessibility Panel" onClick={()=>setOpen(false)}><X size={18}/></button></div><div className="a11y-drawer-content"><section className="a11y-feature-card screen-reader-card"><div className="feature-card-header"><Volume2 size={20}/><div><h3>Read this dashboard aloud</h3><p>Reads the actual visible records on this page.</p></div></div><div className="screen-reader-controls"><button type="button" className="btn-reader-action" onClick={readPage}><Volume2 size={16}/>Read aloud</button><button type="button" className="btn-reader-stop" onClick={()=>{if("speechSynthesis" in window)window.speechSynthesis.cancel();setMessage("Reading stopped.");}}><Square size={14}/>Stop</button></div><p className="customer-a11y-note">Read aloud uses speech synthesis and does not use the microphone.</p></section><section className="a11y-feature-card screen-reader-card"><div className="feature-card-header"><Mic size={20}/><div><h3>Speech-to-text draft</h3><p>Speak a note, then review and edit it yourself.</p></div></div><p className="customer-a11y-note">Start dictation requests microphone access. Your browser may send audio to its speech provider. Nothing is submitted to SolarOps or stored as a business record.</p><div className="screen-reader-controls"><button type="button" className="btn-reader-action" disabled={listening} onClick={startDictation}><Mic size={16}/>{listening?"Listening…":"Start dictation"}</button><button type="button" className="btn-reader-stop" disabled={!listening} onClick={()=>{stopDictation();setMessage("Dictation stopped. Review your draft before using it.");}}><Square size={14}/>Stop dictation</button></div><label className="customer-a11y-note" htmlFor="customer-dictation-draft">Editable dictation draft</label><textarea id="customer-dictation-draft" value={transcript} onChange={e=>setTranscript(e.target.value)} rows={4} style={{width:"100%",background:"#fff",color:"#111827",padding:"10px",borderRadius:"10px",marginTop:"8px"}}/><button type="button" className="customer-a11y-reset" onClick={()=>setTranscript("")}>Clear draft</button></section>{([{key:"contrast",label:"High contrast",detail:"Clear text and stronger boundaries",Icon:Eye},{key:"large",label:"Larger text",detail:"Increase dashboard reading size",Icon:Type},{key:"spacing",label:"Reading spacing",detail:"More space between letters and lines",Icon:Type},{key:"motion",label:"Reduce motion",detail:"Stop decorative motion and transitions",Icon:Sparkles}] as const).map(({key,label,detail,Icon})=><section className="a11y-feature-card" key={key}><div className="feature-card-header"><Icon size={19}/><div><h3>{label}</h3><p>{detail}</p></div><button type="button" className={`a11y-toggle-switch ${preferences[key]?"active":""}`} aria-label={`Toggle ${label}`} aria-pressed={preferences[key]} onClick={()=>setPreferences(p=>({...p,[key]:!p[key]}))}><span className="customer-toggle-dot"/></button></div></section>)}<button type="button" className="customer-a11y-reset" onClick={()=>setPreferences(DEFAULTS)}>Reset accessibility preferences</button><p className="customer-a11y-note">Preferences stay in this browser. Your account and business records are unchanged.</p>{message&&<p role="status">{message}</p>}</div></div></ModalFrame>}</aside>;
}
