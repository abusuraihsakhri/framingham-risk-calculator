/* Framingham 2008 general cardiovascular disease: lipid-based model. */
(function(root){
"use strict";
const agePts={male:[0,2,5,6,8,10,11,12,14],female:[0,2,4,5,7,8,9,10,11]};
const tcPts={male:[0,1,2,3,4],female:[0,1,3,4,5]};
const bpPts={male:{yes:[0,2,3,4,5],no:[-2,0,1,2,3]},female:{yes:[-1,2,3,5,6,7],no:[-3,0,1,2,4,5]}};
const parms={male:[3.06117,1.12370,-.93263,1.93303,1.99881,.65451,.57367,23.9802,.88936],
female:[2.32888,1.20904,-.70833,2.76157,2.82263,.52873,.69154,26.1931,.95012]};
const chart={male:{'-2':1.1,'-1':1.4,...Object.fromEntries([1.6,1.9,2.3,2.8,3.3,3.9,4.7,5.6,6.7,7.9,9.4,11.2,13.2,15.6,18.4,21.6,25.3,29.4].map((r,i)=>[i,r]))},
female:{'-1':1.0,...Object.fromEntries([1.2,1.5,1.7,2,2.4,2.8,3.3,3.9,4.5,5.3,6.3,7.3,8.6,10,11.7,13.7,15.9,18.5,21.5,24.8,28.5].map((r,i)=>[i,r]))}};
function assess({age,sex,tc,hdl,sbp,treated,smoker,diabetic}){
if(!Object.hasOwn(parms,sex)) throw Error("Sex must be male or female");
if(!Number.isInteger(age)||age<30||age>74) throw Error("Age must be an integer from 30 to 74");
for(const [name,v] of [["Total cholesterol",tc],["HDL cholesterol",hdl],["Systolic BP",sbp]])
 if(!Number.isFinite(v)||v<=0) throw Error(name+" must be finite and positive");
if([treated,smoker,diabetic].some(x=>typeof x!=="boolean"))throw Error("Risk flags must be boolean");
const tcI=tc<160?0:tc<200?1:tc<240?2:tc<280?3:4;
const bpI=sex==="male"?(sbp<120?0:sbp<130?1:sbp<140?2:sbp<160?3:4):
(sbp<120?0:sbp<130?1:sbp<140?2:sbp<150?3:sbp<160?4:5);
const breakdown={age_points:agePts[sex][Math.floor((age-30)/5)],
cholesterol_points:tcPts[sex][tcI],hdl_points:hdl<35?2:hdl<45?1:hdl<50?0:hdl<60?-1:-2,
blood_pressure_points:bpPts[sex][treated?"yes":"no"][bpI],
smoking_points:smoker?(sex==="male"?4:3):0,
diabetes_points:diabetic?(sex==="male"?3:4):0};
const total_points=Object.values(breakdown).reduce((a,b)=>a+b,0);
const [a,c,h,su,st,sm,d,mean,survival]=parms[sex];
const lp=a*Math.log(age)+c*Math.log(tc)+h*Math.log(hdl)+(treated?st:su)*Math.log(sbp)+sm*Number(smoker)+d*Number(diabetic)-mean;
const risk_percent=Math.round(-1000*Math.expm1(Math.log(survival)*Math.exp(Math.min(lp,700))))/10;
const point_risk_percent=Object.hasOwn(chart[sex],total_points)?chart[sex][total_points]:null;
const point_risk_label=point_risk_percent===null?(total_points<(sex==="male"?-2:-1)?"<1%":">30%"):point_risk_percent.toFixed(1)+"%";
return {total_points,risk_percent,risk_category:risk_percent<10?"Low":risk_percent<=20?"Intermediate":"High",
breakdown,point_risk_percent,point_risk_label,model:"Framingham 2008 general CVD (lipid-based)"};
}
function flag(value,name){
const text=String(value??"").trim().toLowerCase();
if(["1","true","yes","y"].includes(text))return true;
if(["0","false","no","n",""].includes(text))return false;
throw Error(name+" must be yes/no, true/false or 1/0");
}
function fromRow(row){
const normalized=Object.fromEntries(Object.entries(row).map(([k,v])=>[k.trim().toLowerCase(),v]));
function get(names,optional=false){
for(const n of names)if(Object.hasOwn(normalized,n))return normalized[n];
if(optional)return "0";
throw Error("Missing required field: "+names[0]);
}
return assess({age:Number(get(["age"])),sex:String(get(["sex"])).trim().toLowerCase(),
tc:Number(get(["total_cholesterol","tc"])),hdl:Number(get(["hdl_cholesterol","hdl"])),
sbp:Number(get(["systolic_bp","sbp"])),
treated:flag(get(["bp_treated","on_bp_meds","bp_medication"],true),"bp_treated"),
smoker:flag(get(["smoker","smoking","current_smoker"],true),"smoker"),
diabetic:flag(get(["diabetic","diabetes"],true),"diabetic")});
}
function parseCsv(src){
const lines=[];let cells=[],field="",quotes=false,start=true;
for(let i=0;i<src.length;i++){
const c=src[i];
if(quotes){
if(c==='"'&&src[i+1]==='"'){field+='"';i++}
else if(c==='"')quotes=false;else field+=c;
}else if(c==='"'&&start){quotes=true;start=false}
else if(c===','){cells.push(field);field="";start=true}
else if(c==='\n'||c==='\r'){
if(c==='\r'&&src[i+1]==='\n')i++;
cells.push(field);if(cells.some(v=>v.length))lines.push(cells);
cells=[];field="";start=true;
}else{if(c==='"')throw Error("Invalid CSV quoting");field+=c;start=false}
}
if(quotes)throw Error("Unclosed CSV quotation");
if(field||cells.length){cells.push(field);lines.push(cells)}
if(!lines.length)throw Error("Empty CSV");
const headers=lines.shift().map((h,i)=>i===0?h.replace(/^\uFEFF/,""):h);
const normalized=headers.map(h=>h.trim().toLowerCase());
if(headers.some(h=>!h.trim())||new Set(normalized).size!==headers.length)throw Error("Invalid or duplicate CSV headers");
if(["total_points","risk_percent","risk_category","risk_error"].some(x=>normalized.includes(x)))throw Error("Reserved output columns in input");
return {headers,rows:lines.map(c=>{
if(c.length!==headers.length)throw Error("Incorrect CSV column count");
return Object.fromEntries(headers.map((h,i)=>[h,c[i]]))})};
}
function csvResults(text){
const {headers,rows}=parseCsv(text);
if(rows.length>5000)throw Error("Maximum 5,000 CSV rows");
let errors=0;
const quote=v=>{
let s=String(v??"");
if(/^\s*[=+@-]/.test(s))s="'"+s;
return '"'+s.replace(/"/g,'""')+'"';
};
const cols=[...headers,"total_points","risk_percent","risk_category","risk_error"];
const data=[cols.map(quote).join(",")];
for(const row of rows){
let values;
try{const r=fromRow(row);values=[r.total_points,r.risk_percent,r.risk_category,""]}
catch(e){errors++;values=["ERROR","ERROR","ERROR",e.message]}
data.push([...headers.map(h=>row[h]),...values].map(quote).join(","));
}
return {count:rows.length,errors,csv:data.join("\r\n")+"\r\n"};
}
const api={assess,fromRow,parseCsv,csvResults};
if(typeof module==="object"&&module.exports)module.exports=api;
root.Framingham=api;
})(typeof window!=="undefined"?window:globalThis);
