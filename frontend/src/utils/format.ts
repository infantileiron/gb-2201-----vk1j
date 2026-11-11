export const percent=(v:number|null)=>v===null?'未观测':(v*100).toFixed(1)+'%';
export const decimal=(v:number|null|undefined)=>v==null?'不可识别':v.toFixed(2);
