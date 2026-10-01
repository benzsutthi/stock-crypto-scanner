function calculateAverageCost({oldPrice,oldQuantity,newPrice,newQuantity,fees=0}) {
  if (![oldPrice,oldQuantity,newPrice,newQuantity,fees].every(Number.isFinite)) throw new Error('กรุณากรอกตัวเลขที่ถูกต้องให้ครบ');
  if (oldPrice<=0||oldQuantity<=0||newPrice<=0||newQuantity<=0) throw new Error('ราคาและจำนวนต้องมากกว่า 0');
  if (fees<0) throw new Error('ค่าธรรมเนียมต้องไม่ติดลบ');
  const oldCost=oldPrice*oldQuantity;
  const newCost=newPrice*newQuantity+fees;
  const totalQuantity=oldQuantity+newQuantity;
  const totalCost=oldCost+newCost;
  const average=totalCost/totalQuantity;
  const difference=average-oldPrice;
  const differencePercent=difference/oldPrice*100;
  if (![oldCost,newCost,totalQuantity,totalCost,average,differencePercent].every(Number.isFinite)||average<=0) throw new Error('ตัวเลขสูงหรือต่ำเกินขอบเขตที่คำนวณได้');
  return {oldCost,newCost,totalQuantity,totalCost,average,difference,differencePercent};
}

if (typeof module!=='undefined'&&module.exports) module.exports={calculateAverageCost};

if (typeof document!=='undefined') {
  const form=document.querySelector('#average-form');
  const fields=['old-price','old-quantity','new-price','new-quantity','fees'];
  const format=n=>n!==0&&Math.abs(n)<1e-8?n.toExponential(6):new Intl.NumberFormat('th-TH',{minimumFractionDigits:2,maximumFractionDigits:8}).format(n);
  const quantity=n=>n>0&&n<1e-8?n.toExponential(6):new Intl.NumberFormat('th-TH',{maximumFractionDigits:8}).format(n);
  function clearResults(){
    for(const id of ['average','total-quantity','old-cost','new-cost','total-cost']) document.querySelector('#'+id).textContent='—';
    document.querySelector('#average-change').textContent='กรอกข้อมูลเพื่อดูผลการคำนวณ';
    document.querySelector('#average-change').className='';
  }
  function update(showErrors=false){
    const error=document.querySelector('#input-error');error.textContent='';
    document.querySelector('#result-asset').textContent=document.querySelector('#asset-name').value.trim()||'สินทรัพย์ของคุณ';
    let missing=false;
    fields.forEach(id=>{const input=document.querySelector('#'+id);const value=input.value.trim();const invalid=(id!=='fees'&&value==='')||(value!==''&&(!Number.isFinite(Number(value))||(id==='fees'?Number(value)<0:Number(value)<=0)));input.setAttribute('aria-invalid',String(showErrors&&invalid));if(id!=='fees'&&value==='')missing=true;});
    if(missing){clearResults();if(showErrors)error.textContent='กรุณากรอกราคาและจำนวนทั้งสองรายการให้ครบ';return;}
    try{
      const result=calculateAverageCost({oldPrice:Number(document.querySelector('#old-price').value),oldQuantity:Number(document.querySelector('#old-quantity').value),newPrice:Number(document.querySelector('#new-price').value),newQuantity:Number(document.querySelector('#new-quantity').value),fees:Number(document.querySelector('#fees').value||0)});
      const currency=document.querySelector('#currency').value;
      document.querySelector('#average').textContent=`${format(result.average)} ${currency}`;
      document.querySelector('#total-quantity').textContent=`${quantity(result.totalQuantity)} หน่วย`;
      for(const [id,key] of [['old-cost','oldCost'],['new-cost','newCost'],['total-cost','totalCost']]) document.querySelector('#'+id).textContent=`${format(result[key])} ${currency}`;
      const change=document.querySelector('#average-change');
      change.textContent=Math.abs(result.difference)<=Number.EPSILON*Math.abs(Number(document.querySelector('#old-price').value))*4?'ต้นทุนเฉลี่ยเท่าเดิม':`ต้นทุน${result.difference<0?'ลดลง':'เพิ่มขึ้น'} ${format(Math.abs(result.difference))} ${currency} / หน่วย (${format(Math.abs(result.differencePercent))}%)`;
      change.className=result.difference<0?'cost-down':result.difference>0?'cost-up':'';
    }catch(e){clearResults();error.textContent=e.message;}
  }
  form.addEventListener('submit',e=>{e.preventDefault();update(true);});
  form.addEventListener('input',()=>update());
  form.addEventListener('change',()=>update());
  form.addEventListener('reset',()=>{setTimeout(()=>{fields.forEach(id=>document.querySelector('#'+id).removeAttribute('aria-invalid'));document.querySelector('#input-error').textContent='';document.querySelector('#result-asset').textContent='สินทรัพย์ของคุณ';clearResults();},0);});
  document.querySelector('#example').addEventListener('click',()=>{for(const [id,value] of Object.entries({'asset-name':'หุ้น A','currency':'THB','old-price':'100','old-quantity':'1000','new-price':'80','new-quantity':'1000','fees':'0'}))document.querySelector('#'+id).value=value;update();});
}
