export const $ = selector => document.querySelector(selector);
export function element(tag,text,className){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(className)e.className=className;return e;}
export function button(text,action){const b=element('button',text);b.type='button';b.addEventListener('click',action);return b;}
export function options(select,records,empty){const value=select.value;select.replaceChildren();if(empty!==undefined){const o=element('option',empty);o.value='';select.append(o);}for(const r of records){const o=element('option',r.name);o.value=r.id;select.append(o);}select.value=value;}
export function message(text){$('#message').textContent=text;$('#message').hidden=false;}
export async function request(url,method='GET',body){const res=await fetch(url,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':$('meta[name="csrf-token"]').content},body:body?JSON.stringify(body):undefined});const data=await res.json();if(!res.ok)throw new Error(data.error||'Permintaan gagal.');return data;}
export function data(form){return Object.fromEntries(new FormData(form));}
export function fill(form,record){form.reset();for(const [key,value] of Object.entries(record)){if(form.elements.namedItem(key))form.elements.namedItem(key).value=value;}}
export function error(form,text){form.querySelector('.form-error').textContent=text;}
export function timestamp(value){return new Date(value).toLocaleString('id-ID',{timeZone:'Asia/Jakarta'})+' WIB';}
