'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {assess,fromRow,parseCsv,csvResults}=require('./risk.js');
const base={age:61,sex:'female',tc:230,hdl:47,sbp:124,treated:false,smoker:false,diabetic:false};

test('published 2008 female point-score example',()=>{
  const r=assess(base);
  assert.equal(r.total_points,12);
  assert.equal(r.point_risk_percent,8.6);
  assert.equal(r.risk_percent,8.4);
});
test('male point score and risk',()=>{
  const r=assess({age:55,sex:'male',tc:220,hdl:45,sbp:135,treated:false,smoker:true,diabetic:false});
  assert.equal(r.total_points,17);
  assert.equal(r.point_risk_percent,29.4);
});
test('invalid inputs are rejected',()=>{
  for(const age of [29,75,50.1,NaN,Infinity])assert.throws(()=>assess({...base,age}));
  for(const tc of [0,-1,NaN,Infinity])assert.throws(()=>assess({...base,tc}));
  assert.throws(()=>assess({...base,sex:'unknown'}));
  assert.throws(()=>assess({...base,treated:1}));
});
test('CSV quoted records and invalid flags',()=>{
  const src='age,sex,tc,hdl,sbp,smoker,note\r\n61,female,230,47,124,no,"contains, comma"\r\n50,male,200,40,140,maybe,"bad"\r\n';
  const parsed=parseCsv(src);
  assert.equal(parsed.rows[0].note,'contains, comma');
  assert.equal(parsed.rows.length,2);
  const scored=csvResults(src);
  assert.equal(scored.count,2);
  assert.equal(scored.errors,1);
  assert.match(scored.csv,/ERROR/);
  assert.match(scored.csv,/"8.4"/);
  assert.equal(fromRow(parsed.rows[0]).total_points,12);
});
test('CSV detects duplicate headers and invalid quoting',()=>{
  assert.throws(()=>parseCsv('age,AGE\n50,50'));
  assert.throws(()=>parseCsv('a,b\n1,2,3'));
  assert.throws(()=>parseCsv('a,b\n"unterminated'));
});
test('CSV export protects against spreadsheet formula injection',()=>{
  const x=csvResults('age,sex,tc,hdl,sbp,note\n61,female,230,47,124,"=SUM(1,2)"');
  assert.match(x.csv,/"'=SUM\(1,2\)"/);
});
