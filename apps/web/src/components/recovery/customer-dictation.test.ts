import { expect, it } from "vitest";
import { finalDictationText, dictationFailure } from "./customer-accessibility";
it("only appends new finalized recognition results, without repeating earlier phrases",()=>{
 expect(finalDictationText({resultIndex:1,results:[{isFinal:true,0:{transcript:"Earlier phrase"}},{isFinal:false,0:{transcript:"Interim speculation"}},{isFinal:true,0:{transcript:"  Real final phrase  "}}]})).toBe("Real final phrase");
});
it("does not fabricate text for missing, blank or interim recognition",()=>{
 expect(finalDictationText({resultIndex:0,results:[{isFinal:true},{isFinal:true,0:{transcript:" "}},{isFinal:false,0:{transcript:"Not final"}}]})).toBe("");
});
it("keeps permission and unsupported errors honest instead of producing a success draft",()=>{
 expect(dictationFailure("not-allowed")).toContain("permission was denied");
 expect(dictationFailure("no-speech")).toContain("existing draft is unchanged");
 expect(dictationFailure("audio-capture")).toContain("No microphone");
 expect(dictationFailure("network")).toContain("unavailable or interrupted");
});
