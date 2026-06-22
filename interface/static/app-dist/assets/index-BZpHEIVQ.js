const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/agents-view-DxoeWgt8.js","assets/ds-panel-B0Coku7q.js","assets/ds-button-X_d22ss4.js","assets/research-view-BG3oOpgp.js","assets/science-view-Bn0GBYGI.js","assets/math-LGDZ9YcA.js","assets/calc-view-DASy92gl.js","assets/missions-view-BTJznA1X.js","assets/network-view-BYibjHQw.js","assets/etis-hud-DvIJLd5L.js","assets/system-monitor-BhQ5iErD.js","assets/geo-view-DEpC7TJh.js","assets/audit-view-BuOe0SoZ.js","assets/finance-view-CYWrJXd7.js","assets/email-view-CU2o6-X2.js","assets/projects-view-BWOaguFa.js"])))=>i.map(i=>d[i]);
(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))r(i);new MutationObserver(i=>{for(const o of i)if(o.type==="childList")for(const n of o.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&r(n)}).observe(document,{childList:!0,subtree:!0});function s(i){const o={};return i.integrity&&(o.integrity=i.integrity),i.referrerPolicy&&(o.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?o.credentials="include":i.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function r(i){if(i.ep)return;i.ep=!0;const o=s(i);fetch(i.href,o)}})();var ms=Object.defineProperty,vs=(e,t,s)=>t in e?ms(e,t,{enumerable:!0,configurable:!0,writable:!0,value:s}):e[t]=s,Ye=(e,t,s)=>(vs(e,typeof t!="symbol"?t+"":t,s),s),gs=(e,t,s)=>{if(!t.has(e))throw TypeError("Cannot "+s)},Ke=(e,t)=>{if(Object(t)!==t)throw TypeError('Cannot use the "in" operator on this value');return e.has(t)},Oe=(e,t,s)=>{if(t.has(e))throw TypeError("Cannot add the same private member more than once");t instanceof WeakSet?t.add(e):t.set(e,s)},wt=(e,t,s)=>(gs(e,t,"access private method"),s);/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Ht(e,t){return Object.is(e,t)}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */let w=null,ye=!1,Ne=1;const De=Symbol("SIGNAL");function de(e){const t=w;return w=e,t}function bs(){return w}function ys(){return ye}const ct={version:0,lastCleanEpoch:0,dirty:!1,producerNode:void 0,producerLastReadVersion:void 0,producerIndexOfThis:void 0,nextProducerIndex:0,liveConsumerNode:void 0,liveConsumerIndexOfThis:void 0,consumerAllowSignalWrites:!1,consumerIsAlwaysLive:!1,producerMustRecompute:()=>!1,producerRecomputeValue:()=>{},consumerMarkedDirty:()=>{},consumerOnSignalRead:()=>{}};function Ve(e){if(ye)throw new Error(typeof ngDevMode<"u"&&ngDevMode?"Assertion error: signal read during notification phase":"");if(w===null)return;w.consumerOnSignalRead(e);const t=w.nextProducerIndex++;if(he(w),t<w.producerNode.length&&w.producerNode[t]!==e&&it(w)){const s=w.producerNode[t];Ge(s,w.producerIndexOfThis[t])}w.producerNode[t]!==e&&(w.producerNode[t]=e,w.producerIndexOfThis[t]=it(w)?Gt(e,w,t):0),w.producerLastReadVersion[t]=e.version}function _s(){Ne++}function qt(e){if(!(!e.dirty&&e.lastCleanEpoch===Ne)){if(!e.producerMustRecompute(e)&&!ks(e)){e.dirty=!1,e.lastCleanEpoch=Ne;return}e.producerRecomputeValue(e),e.dirty=!1,e.lastCleanEpoch=Ne}}function Vt(e){if(e.liveConsumerNode===void 0)return;const t=ye;ye=!0;try{for(const s of e.liveConsumerNode)s.dirty||xs(s)}finally{ye=t}}function ws(){return(w==null?void 0:w.consumerAllowSignalWrites)!==!1}function xs(e){var t;e.dirty=!0,Vt(e),(t=e.consumerMarkedDirty)==null||t.call(e.wrapper??e)}function $s(e){return e&&(e.nextProducerIndex=0),de(e)}function Ss(e,t){if(de(t),!(!e||e.producerNode===void 0||e.producerIndexOfThis===void 0||e.producerLastReadVersion===void 0)){if(it(e))for(let s=e.nextProducerIndex;s<e.producerNode.length;s++)Ge(e.producerNode[s],e.producerIndexOfThis[s]);for(;e.producerNode.length>e.nextProducerIndex;)e.producerNode.pop(),e.producerLastReadVersion.pop(),e.producerIndexOfThis.pop()}}function ks(e){he(e);for(let t=0;t<e.producerNode.length;t++){const s=e.producerNode[t],r=e.producerLastReadVersion[t];if(r!==s.version||(qt(s),r!==s.version))return!0}return!1}function Gt(e,t,s){var r;if(lt(e),he(e),e.liveConsumerNode.length===0){(r=e.watched)==null||r.call(e.wrapper);for(let i=0;i<e.producerNode.length;i++)e.producerIndexOfThis[i]=Gt(e.producerNode[i],e,i)}return e.liveConsumerIndexOfThis.push(s),e.liveConsumerNode.push(t)-1}function Ge(e,t){var s;if(lt(e),he(e),typeof ngDevMode<"u"&&ngDevMode&&t>=e.liveConsumerNode.length)throw new Error(`Assertion error: active consumer index ${t} is out of bounds of ${e.liveConsumerNode.length} consumers)`);if(e.liveConsumerNode.length===1){(s=e.unwatched)==null||s.call(e.wrapper);for(let i=0;i<e.producerNode.length;i++)Ge(e.producerNode[i],e.producerIndexOfThis[i])}const r=e.liveConsumerNode.length-1;if(e.liveConsumerNode[t]=e.liveConsumerNode[r],e.liveConsumerIndexOfThis[t]=e.liveConsumerIndexOfThis[r],e.liveConsumerNode.length--,e.liveConsumerIndexOfThis.length--,t<e.liveConsumerNode.length){const i=e.liveConsumerIndexOfThis[t],o=e.liveConsumerNode[t];he(o),o.producerIndexOfThis[i]=t}}function it(e){var t;return e.consumerIsAlwaysLive||(((t=e==null?void 0:e.liveConsumerNode)==null?void 0:t.length)??0)>0}function he(e){e.producerNode??(e.producerNode=[]),e.producerIndexOfThis??(e.producerIndexOfThis=[]),e.producerLastReadVersion??(e.producerLastReadVersion=[])}function lt(e){e.liveConsumerNode??(e.liveConsumerNode=[]),e.liveConsumerIndexOfThis??(e.liveConsumerIndexOfThis=[])}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Bt(e){if(qt(e),Ve(e),e.value===rt)throw e.error;return e.value}function Cs(e){const t=Object.create(As);t.computation=e;const s=()=>Bt(t);return s[De]=t,s}const Xe=Symbol("UNSET"),Je=Symbol("COMPUTING"),rt=Symbol("ERRORED"),As={...ct,value:Xe,dirty:!0,error:null,equal:Ht,producerMustRecompute(e){return e.value===Xe||e.value===Je},producerRecomputeValue(e){if(e.value===Je)throw new Error("Detected cycle in computations.");const t=e.value;e.value=Je;const s=$s(e);let r,i=!1;try{r=e.computation.call(e.wrapper),i=t!==Xe&&t!==rt&&e.equal.call(e.wrapper,t,r)}catch(o){r=rt,e.error=o}finally{Ss(e,s)}if(i){e.value=t;return}e.value=r,e.version++}};/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Es(){throw new Error}let Ps=Es;function Ts(){Ps()}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Os(e){const t=Object.create(Is);t.value=e;const s=()=>(Ve(t),t.value);return s[De]=t,s}function Ms(){return Ve(this),this.value}function Ns(e,t){ws()||Ts(),e.equal.call(e.wrapper,e.value,t)||(e.value=t,Rs(e))}const Is={...ct,equal:Ht,value:void 0};function Rs(e){e.version++,_s(),Vt(e)}/**
 * @license
 * Copyright 2024 Bloomberg Finance L.P.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const S=Symbol("node");var G;(e=>{var t,s,r,i;class o{constructor(c,l={}){Oe(this,s),Ye(this,t);const d=Os(c)[De];if(this[S]=d,d.wrapper=this,l){const p=l.equals;p&&(d.equal=p),d.watched=l[e.subtle.watched],d.unwatched=l[e.subtle.unwatched]}}get(){if(!(0,e.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.get");return Ms.call(this[S])}set(c){if(!(0,e.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.set");if(ys())throw new Error("Writes to signals not permitted during Watcher callback");const l=this[S];Ns(l,c)}}t=S,s=new WeakSet,e.isState=a=>typeof a=="object"&&Ke(s,a),e.State=o;class n{constructor(c,l){Oe(this,i),Ye(this,r);const d=Cs(c)[De];if(d.consumerAllowSignalWrites=!0,this[S]=d,d.wrapper=this,l){const p=l.equals;p&&(d.equal=p),d.watched=l[e.subtle.watched],d.unwatched=l[e.subtle.unwatched]}}get(){if(!(0,e.isComputed)(this))throw new TypeError("Wrong receiver type for Signal.Computed.prototype.get");return Bt(this[S])}}r=S,i=new WeakSet,e.isComputed=a=>typeof a=="object"&&Ke(i,a),e.Computed=n,(a=>{var c,l,h,d;function p(m){let v,u=null;try{u=de(null),v=m()}finally{de(u)}return v}a.untrack=p;function g(m){var v;if(!(0,e.isComputed)(m)&&!(0,e.isWatcher)(m))throw new TypeError("Called introspectSources without a Computed or Watcher argument");return((v=m[S].producerNode)==null?void 0:v.map(u=>u.wrapper))??[]}a.introspectSources=g;function y(m){var v;if(!(0,e.isComputed)(m)&&!(0,e.isState)(m))throw new TypeError("Called introspectSinks without a Signal argument");return((v=m[S].liveConsumerNode)==null?void 0:v.map(u=>u.wrapper))??[]}a.introspectSinks=y;function O(m){if(!(0,e.isComputed)(m)&&!(0,e.isState)(m))throw new TypeError("Called hasSinks without a Signal argument");const v=m[S].liveConsumerNode;return v?v.length>0:!1}a.hasSinks=O;function M(m){if(!(0,e.isComputed)(m)&&!(0,e.isWatcher)(m))throw new TypeError("Called hasSources without a Computed or Watcher argument");const v=m[S].producerNode;return v?v.length>0:!1}a.hasSources=M;class N{constructor(v){Oe(this,l),Oe(this,h),Ye(this,c);let u=Object.create(ct);u.wrapper=this,u.consumerMarkedDirty=v,u.consumerIsAlwaysLive=!0,u.consumerAllowSignalWrites=!1,u.producerNode=[],this[S]=u}watch(...v){if(!(0,e.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");wt(this,h,d).call(this,v);const u=this[S];u.dirty=!1;const _=de(u);for(const k of v)Ve(k[S]);de(_)}unwatch(...v){if(!(0,e.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");wt(this,h,d).call(this,v);const u=this[S];he(u);for(let _=u.producerNode.length-1;_>=0;_--)if(v.includes(u.producerNode[_].wrapper)){Ge(u.producerNode[_],u.producerIndexOfThis[_]);const k=u.producerNode.length-1;if(u.producerNode[_]=u.producerNode[k],u.producerIndexOfThis[_]=u.producerIndexOfThis[k],u.producerNode.length--,u.producerIndexOfThis.length--,u.nextProducerIndex--,_<u.producerNode.length){const I=u.producerIndexOfThis[_],R=u.producerNode[_];lt(R),R.liveConsumerIndexOfThis[I]=_}}}getPending(){if(!(0,e.isWatcher)(this))throw new TypeError("Called getPending without Watcher receiver");return this[S].producerNode.filter(u=>u.dirty).map(u=>u.wrapper)}}c=S,l=new WeakSet,h=new WeakSet,d=function(m){for(const v of m)if(!(0,e.isComputed)(v)&&!(0,e.isState)(v))throw new TypeError("Called watch/unwatch without a Computed or State argument")},e.isWatcher=m=>Ke(l,m),a.Watcher=N;function z(){var m;return(m=bs())==null?void 0:m.wrapper}a.currentComputed=z,a.watched=Symbol("watched"),a.unwatched=Symbol("unwatched")})(e.subtle||(e.subtle={}))})(G||(G={}));/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ds=Symbol("SignalWatcherBrand"),Ls=new FinalizationRegistry((({watcher:e,signal:t})=>{e.unwatch(t)})),xt=new WeakMap;function Yt(e){return e[Ds]===!0?(console.warn("SignalWatcher should not be applied to the same class more than once."),e):class extends e{constructor(){super(...arguments),this._$St=new G.State(0),this._$Si=!1,this._$So=!0,this._$Sh=new Set}_$Sl(){if(this._$Su!==void 0)return;this._$Sv=new G.Computed((()=>{this._$St.get(),super.performUpdate()}));const t=this._$Su=new G.subtle.Watcher((function(){const s=xt.get(this);s!==void 0&&(s._$Si===!1&&s.requestUpdate(),this.watch())}));xt.set(t,this),Ls.register(this,{watcher:t,signal:this._$Sv}),t.watch(this._$Sv)}_$Sp(){this._$Su!==void 0&&(this._$Su.unwatch(this._$Sv),this._$Sv=void 0,this._$Su=void 0)}performUpdate(){this.isUpdatePending&&(this._$Sl(),this._$Si=!0,this._$St.set(this._$St.get()+1),this._$Si=!1,this._$Sv.get())}update(t){try{this._$So?(this._$So=!1,super.update(t)):this._$Sh.forEach((s=>s.commit()))}finally{this.isUpdatePending=!1,this._$Sh.clear()}}requestUpdate(t,s,r){this._$So=!0,super.requestUpdate(t,s,r)}connectedCallback(){super.connectedCallback(),this.requestUpdate()}disconnectedCallback(){super.disconnectedCallback(),queueMicrotask((()=>{this.isConnected===!1&&this._$Sp()}))}_(t){this._$Sh.add(t);const s=this._$So;this.requestUpdate(),this._$So=s}m(t){this._$Sh.delete(t)}}}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const _e=globalThis,$t=e=>e,Le=_e.trustedTypes,St=Le?Le.createPolicy("lit-html",{createHTML:e=>e}):void 0,Kt="$lit$",Y=`lit$${Math.random().toFixed(9).slice(2)}$`,Xt="?"+Y,Us=`<${Xt}>`,ie=document,xe=()=>ie.createComment(""),$e=e=>e===null||typeof e!="object"&&typeof e!="function",dt=Array.isArray,zs=e=>dt(e)||typeof(e==null?void 0:e[Symbol.iterator])=="function",Ze=`[ 	
\f\r]`,me=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,kt=/-->/g,Ct=/>/g,Q=RegExp(`>|${Ze}(?:([^\\s"'>=/]+)(${Ze}*=${Ze}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),At=/'/g,Et=/"/g,Jt=/^(?:script|style|textarea|title)$/i,Zt=e=>(t,...s)=>({_$litType$:e,strings:t,values:s}),f=Zt(1),Zi=Zt(2),pe=Symbol.for("lit-noChange"),$=Symbol.for("lit-nothing"),Pt=new WeakMap,ee=ie.createTreeWalker(ie,129);function Qt(e,t){if(!dt(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return St!==void 0?St.createHTML(t):t}const Ws=(e,t)=>{const s=e.length-1,r=[];let i,o=t===2?"<svg>":t===3?"<math>":"",n=me;for(let a=0;a<s;a++){const c=e[a];let l,h,d=-1,p=0;for(;p<c.length&&(n.lastIndex=p,h=n.exec(c),h!==null);)p=n.lastIndex,n===me?h[1]==="!--"?n=kt:h[1]!==void 0?n=Ct:h[2]!==void 0?(Jt.test(h[2])&&(i=RegExp("</"+h[2],"g")),n=Q):h[3]!==void 0&&(n=Q):n===Q?h[0]===">"?(n=i??me,d=-1):h[1]===void 0?d=-2:(d=n.lastIndex-h[2].length,l=h[1],n=h[3]===void 0?Q:h[3]==='"'?Et:At):n===Et||n===At?n=Q:n===kt||n===Ct?n=me:(n=Q,i=void 0);const g=n===Q&&e[a+1].startsWith("/>")?" ":"";o+=n===me?c+Us:d>=0?(r.push(l),c.slice(0,d)+Kt+c.slice(d)+Y+g):c+Y+(d===-2?a:g)}return[Qt(e,o+(e[s]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]};let ot=class es{constructor({strings:t,_$litType$:s},r){let i;this.parts=[];let o=0,n=0;const a=t.length-1,c=this.parts,[l,h]=Ws(t,s);if(this.el=es.createElement(l,r),ee.currentNode=this.el.content,s===2||s===3){const d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(i=ee.nextNode())!==null&&c.length<a;){if(i.nodeType===1){if(i.hasAttributes())for(const d of i.getAttributeNames())if(d.endsWith(Kt)){const p=h[n++],g=i.getAttribute(d).split(Y),y=/([.?@])?(.*)/.exec(p);c.push({type:1,index:o,name:y[2],strings:g,ctor:y[1]==="."?Fs:y[1]==="?"?Hs:y[1]==="@"?qs:Be}),i.removeAttribute(d)}else d.startsWith(Y)&&(c.push({type:6,index:o}),i.removeAttribute(d));if(Jt.test(i.tagName)){const d=i.textContent.split(Y),p=d.length-1;if(p>0){i.textContent=Le?Le.emptyScript:"";for(let g=0;g<p;g++)i.append(d[g],xe()),ee.nextNode(),c.push({type:2,index:++o});i.append(d[p],xe())}}}else if(i.nodeType===8)if(i.data===Xt)c.push({type:2,index:o});else{let d=-1;for(;(d=i.data.indexOf(Y,d+1))!==-1;)c.push({type:7,index:o}),d+=Y.length-1}o++}}static createElement(t,s){const r=ie.createElement("template");return r.innerHTML=t,r}};function ue(e,t,s=e,r){var n,a;if(t===pe)return t;let i=r!==void 0?(n=s._$Co)==null?void 0:n[r]:s._$Cl;const o=$e(t)?void 0:t._$litDirective$;return(i==null?void 0:i.constructor)!==o&&((a=i==null?void 0:i._$AO)==null||a.call(i,!1),o===void 0?i=void 0:(i=new o(e),i._$AT(e,s,r)),r!==void 0?(s._$Co??(s._$Co=[]))[r]=i:s._$Cl=i),i!==void 0&&(t=ue(e,i._$AS(e,t.values),i,r)),t}class js{constructor(t,s){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:s},parts:r}=this._$AD,i=((t==null?void 0:t.creationScope)??ie).importNode(s,!0);ee.currentNode=i;let o=ee.nextNode(),n=0,a=0,c=r[0];for(;c!==void 0;){if(n===c.index){let l;c.type===2?l=new Ae(o,o.nextSibling,this,t):c.type===1?l=new c.ctor(o,c.name,c.strings,this,t):c.type===6&&(l=new Vs(o,this,t)),this._$AV.push(l),c=r[++a]}n!==(c==null?void 0:c.index)&&(o=ee.nextNode(),n++)}return ee.currentNode=ie,i}p(t){let s=0;for(const r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,s),s+=r.strings.length-2):r._$AI(t[s])),s++}}class Ae{get _$AU(){var t;return((t=this._$AM)==null?void 0:t._$AU)??this._$Cv}constructor(t,s,r,i){this.type=2,this._$AH=$,this._$AN=void 0,this._$AA=t,this._$AB=s,this._$AM=r,this.options=i,this._$Cv=(i==null?void 0:i.isConnected)??!0}get parentNode(){let t=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&(t==null?void 0:t.nodeType)===11&&(t=s.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,s=this){t=ue(this,t,s),$e(t)?t===$||t==null||t===""?(this._$AH!==$&&this._$AR(),this._$AH=$):t!==this._$AH&&t!==pe&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):zs(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==$&&$e(this._$AH)?this._$AA.nextSibling.data=t:this.T(ie.createTextNode(t)),this._$AH=t}$(t){var o;const{values:s,_$litType$:r}=t,i=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=ot.createElement(Qt(r.h,r.h[0]),this.options)),r);if(((o=this._$AH)==null?void 0:o._$AD)===i)this._$AH.p(s);else{const n=new js(i,this),a=n.u(this.options);n.p(s),this.T(a),this._$AH=n}}_$AC(t){let s=Pt.get(t.strings);return s===void 0&&Pt.set(t.strings,s=new ot(t)),s}k(t){dt(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let r,i=0;for(const o of t)i===s.length?s.push(r=new Ae(this.O(xe()),this.O(xe()),this,this.options)):r=s[i],r._$AI(o),i++;i<s.length&&(this._$AR(r&&r._$AB.nextSibling,i),s.length=i)}_$AR(t=this._$AA.nextSibling,s){var r;for((r=this._$AP)==null?void 0:r.call(this,!1,!0,s);t!==this._$AB;){const i=$t(t).nextSibling;$t(t).remove(),t=i}}setConnected(t){var s;this._$AM===void 0&&(this._$Cv=t,(s=this._$AP)==null||s.call(this,t))}}class Be{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,s,r,i,o){this.type=1,this._$AH=$,this._$AN=void 0,this.element=t,this.name=s,this._$AM=i,this.options=o,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=$}_$AI(t,s=this,r,i){const o=this.strings;let n=!1;if(o===void 0)t=ue(this,t,s,0),n=!$e(t)||t!==this._$AH&&t!==pe,n&&(this._$AH=t);else{const a=t;let c,l;for(t=o[0],c=0;c<o.length-1;c++)l=ue(this,a[r+c],s,c),l===pe&&(l=this._$AH[c]),n||(n=!$e(l)||l!==this._$AH[c]),l===$?t=$:t!==$&&(t+=(l??"")+o[c+1]),this._$AH[c]=l}n&&!i&&this.j(t)}j(t){t===$?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class Fs extends Be{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===$?void 0:t}}class Hs extends Be{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==$)}}class qs extends Be{constructor(t,s,r,i,o){super(t,s,r,i,o),this.type=5}_$AI(t,s=this){if((t=ue(this,t,s,0)??$)===pe)return;const r=this._$AH,i=t===$&&r!==$||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,o=t!==$&&(r===$||i);i&&this.element.removeEventListener(this.name,this,r),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var s;typeof this._$AH=="function"?this._$AH.call(((s=this.options)==null?void 0:s.host)??this.element,t):this._$AH.handleEvent(t)}}class Vs{constructor(t,s,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=s,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){ue(this,t)}}const Qe=_e.litHtmlPolyfillSupport;Qe==null||Qe(ot,Ae),(_e.litHtmlVersions??(_e.litHtmlVersions=[])).push("3.3.3");const Gs=(e,t,s)=>{const r=(s==null?void 0:s.renderBefore)??t;let i=r._$litPart$;if(i===void 0){const o=(s==null?void 0:s.renderBefore)??null;r._$litPart$=i=new Ae(t.insertBefore(xe(),o),o,void 0,s??{})}return i._$AI(e),i};/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */G.State;G.Computed;const B=(e,t)=>new G.State(e,t),ts=(e,t)=>new G.Computed(e,t),ss="deep_skin",ht=B(localStorage.getItem(ss)||"calm");function is(e){ht.set(e),localStorage.setItem(ss,e),e==="calm"?document.documentElement.removeAttribute("data-skin"):document.documentElement.setAttribute("data-skin",e)}function Bs(){is(ht.get()==="calm"?"neon":"calm")}const Ys={cyan:"#00e5ff",pink:"#d946ef",green:"#10b981",orange:"#f59e0b"},rs="deep_accent",os=B(localStorage.getItem(rs)||"cyan");function Ks(e){os.set(e),localStorage.setItem(rs,e),document.documentElement.style.setProperty("--ds-accent",Ys[e])}is(ht.get());Ks(os.get());const Xs="modulepreload",Js=function(e){return"/static/app-dist/"+e},Tt={},A=function(t,s,r){let i=Promise.resolve();if(s&&s.length>0){let n=function(l){return Promise.all(l.map(h=>Promise.resolve(h).then(d=>({status:"fulfilled",value:d}),d=>({status:"rejected",reason:d}))))};document.getElementsByTagName("link");const a=document.querySelector("meta[property=csp-nonce]"),c=(a==null?void 0:a.nonce)||(a==null?void 0:a.getAttribute("nonce"));i=n(s.map(l=>{if(l=Js(l),l in Tt)return;Tt[l]=!0;const h=l.endsWith(".css"),d=h?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${l}"]${d}`))return;const p=document.createElement("link");if(p.rel=h?"stylesheet":Xs,h||(p.as="script"),p.crossOrigin="",p.href=l,c&&p.setAttribute("nonce",c),document.head.appendChild(p),h)return new Promise((g,y)=>{p.addEventListener("load",g),p.addEventListener("error",()=>y(new Error(`Unable to preload CSS for ${l}`)))})}))}function o(n){const a=new Event("vite:preloadError",{cancelable:!0});if(a.payload=n,window.dispatchEvent(a),!a.defaultPrevented)throw n}return i.then(n=>{for(const a of n||[])a.status==="rejected"&&o(a.reason);return t().catch(o)})};/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ie=globalThis,pt=Ie.ShadowRoot&&(Ie.ShadyCSS===void 0||Ie.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ut=Symbol(),Ot=new WeakMap;let ns=class{constructor(t,s,r){if(this._$cssResult$=!0,r!==ut)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=s}get styleSheet(){let t=this.o;const s=this.t;if(pt&&t===void 0){const r=s!==void 0&&s.length===1;r&&(t=Ot.get(s)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&Ot.set(s,t))}return t}toString(){return this.cssText}};const Zs=e=>new ns(typeof e=="string"?e:e+"",void 0,ut),H=(e,...t)=>{const s=e.length===1?e[0]:t.reduce((r,i,o)=>r+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[o+1],e[0]);return new ns(s,e,ut)},Qs=(e,t)=>{if(pt)e.adoptedStyleSheets=t.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of t){const r=document.createElement("style"),i=Ie.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=s.cssText,e.appendChild(r)}},Mt=pt?e=>e:e=>e instanceof CSSStyleSheet?(t=>{let s="";for(const r of t.cssRules)s+=r.cssText;return Zs(s)})(e):e;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:ei,defineProperty:ti,getOwnPropertyDescriptor:si,getOwnPropertyNames:ii,getOwnPropertySymbols:ri,getPrototypeOf:oi}=Object,K=globalThis,Nt=K.trustedTypes,ni=Nt?Nt.emptyScript:"",et=K.reactiveElementPolyfillSupport,we=(e,t)=>e,Ue={toAttribute(e,t){switch(t){case Boolean:e=e?ni:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let s=e;switch(t){case Boolean:s=e!==null;break;case Number:s=e===null?null:Number(e);break;case Object:case Array:try{s=JSON.parse(e)}catch{s=null}}return s}},ft=(e,t)=>!ei(e,t),It={attribute:!0,type:String,converter:Ue,reflect:!1,useDefault:!1,hasChanged:ft};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),K.litPropertyMetadata??(K.litPropertyMetadata=new WeakMap);class ce extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,s=It){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(t,s),!s.noAccessor){const r=Symbol(),i=this.getPropertyDescriptor(t,r,s);i!==void 0&&ti(this.prototype,t,i)}}static getPropertyDescriptor(t,s,r){const{get:i,set:o}=si(this.prototype,t)??{get(){return this[s]},set(n){this[s]=n}};return{get:i,set(n){const a=i==null?void 0:i.call(this);o==null||o.call(this,n),this.requestUpdate(t,a,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??It}static _$Ei(){if(this.hasOwnProperty(we("elementProperties")))return;const t=oi(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(we("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(we("properties"))){const s=this.properties,r=[...ii(s),...ri(s)];for(const i of r)this.createProperty(i,s[i])}const t=this[Symbol.metadata];if(t!==null){const s=litPropertyMetadata.get(t);if(s!==void 0)for(const[r,i]of s)this.elementProperties.set(r,i)}this._$Eh=new Map;for(const[s,r]of this.elementProperties){const i=this._$Eu(s,r);i!==void 0&&this._$Eh.set(i,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const s=[];if(Array.isArray(t)){const r=new Set(t.flat(1/0).reverse());for(const i of r)s.unshift(Mt(i))}else t!==void 0&&s.push(Mt(t));return s}static _$Eu(t,s){const r=s.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var t;this._$ES=new Promise(s=>this.enableUpdating=s),this._$AL=new Map,this._$E_(),this.requestUpdate(),(t=this.constructor.l)==null||t.forEach(s=>s(this))}addController(t){var s;(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&((s=t.hostConnected)==null||s.call(t))}removeController(t){var s;(s=this._$EO)==null||s.delete(t)}_$E_(){const t=new Map,s=this.constructor.elementProperties;for(const r of s.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Qs(t,this.constructor.elementStyles),t}connectedCallback(){var t;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(t=this._$EO)==null||t.forEach(s=>{var r;return(r=s.hostConnected)==null?void 0:r.call(s)})}enableUpdating(t){}disconnectedCallback(){var t;(t=this._$EO)==null||t.forEach(s=>{var r;return(r=s.hostDisconnected)==null?void 0:r.call(s)})}attributeChangedCallback(t,s,r){this._$AK(t,r)}_$ET(t,s){var o;const r=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,r);if(i!==void 0&&r.reflect===!0){const n=(((o=r.converter)==null?void 0:o.toAttribute)!==void 0?r.converter:Ue).toAttribute(s,r.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,s){var o,n;const r=this.constructor,i=r._$Eh.get(t);if(i!==void 0&&this._$Em!==i){const a=r.getPropertyOptions(i),c=typeof a.converter=="function"?{fromAttribute:a.converter}:((o=a.converter)==null?void 0:o.fromAttribute)!==void 0?a.converter:Ue;this._$Em=i;const l=c.fromAttribute(s,a.type);this[i]=l??((n=this._$Ej)==null?void 0:n.get(i))??l,this._$Em=null}}requestUpdate(t,s,r,i=!1,o){var n;if(t!==void 0){const a=this.constructor;if(i===!1&&(o=this[t]),r??(r=a.getPropertyOptions(t)),!((r.hasChanged??ft)(o,s)||r.useDefault&&r.reflect&&o===((n=this._$Ej)==null?void 0:n.get(t))&&!this.hasAttribute(a._$Eu(t,r))))return;this.C(t,s,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,s,{useDefault:r,reflect:i,wrapped:o},n){r&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,n??s??this[t]),o!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(s=void 0),this._$AL.set(t,s)),i===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var r;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[o,n]of this._$Ep)this[o]=n;this._$Ep=void 0}const i=this.constructor.elementProperties;if(i.size>0)for(const[o,n]of i){const{wrapped:a}=n,c=this[o];a!==!0||this._$AL.has(o)||c===void 0||this.C(o,void 0,n,c)}}let t=!1;const s=this._$AL;try{t=this.shouldUpdate(s),t?(this.willUpdate(s),(r=this._$EO)==null||r.forEach(i=>{var o;return(o=i.hostUpdate)==null?void 0:o.call(i)}),this.update(s)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(s)}willUpdate(t){}_$AE(t){var s;(s=this._$EO)==null||s.forEach(r=>{var i;return(i=r.hostUpdated)==null?void 0:i.call(r)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(s=>this._$ET(s,this[s]))),this._$EM()}updated(t){}firstUpdated(t){}}ce.elementStyles=[],ce.shadowRootOptions={mode:"open"},ce[we("elementProperties")]=new Map,ce[we("finalized")]=new Map,et==null||et({ReactiveElement:ce}),(K.reactiveElementVersions??(K.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const se=globalThis;class E extends ce{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var s;const t=super.createRenderRoot();return(s=this.renderOptions).renderBefore??(s.renderBefore=t.firstChild),t}update(t){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Gs(s,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),(t=this._$Do)==null||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),(t=this._$Do)==null||t.setConnected(!1)}render(){return pe}}var Ft;E._$litElement$=!0,E.finalized=!0,(Ft=se.litElementHydrateSupport)==null||Ft.call(se,{LitElement:E});const tt=se.litElementPolyfillSupport;tt==null||tt({LitElement:E});(se.litElementVersions??(se.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const q=e=>(t,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const ai={attribute:!0,type:String,converter:Ue,reflect:!1,hasChanged:ft},ci=(e=ai,t,s)=>{const{kind:r,metadata:i}=s;let o=globalThis.litPropertyMetadata.get(i);if(o===void 0&&globalThis.litPropertyMetadata.set(i,o=new Map),r==="setter"&&((e=Object.create(e)).wrapped=!0),o.set(s.name,e),r==="accessor"){const{name:n}=s;return{set(a){const c=t.get.call(this);t.set.call(this,a),this.requestUpdate(n,c,e,!0,a)},init(a){return a!==void 0&&this.C(n,void 0,e,a),a}}}if(r==="setter"){const{name:n}=s;return function(a){const c=this[n];t.call(this,a),this.requestUpdate(n,c,e,!0,a)}}throw Error("Unsupported decorator location: "+r)};function V(e){return(t,s)=>typeof s=="object"?ci(e,t,s):((r,i,o)=>{const n=i.hasOwnProperty(o);return i.constructor.createProperty(o,r),n?Object.getOwnPropertyDescriptor(i,o):void 0})(e,t,s)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function x(e){return V({...e,state:!0,attribute:!1})}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const li=(e,t,s)=>(s.configurable=!0,s.enumerable=!0,Reflect.decorate&&typeof t!="object"&&Object.defineProperty(e,t,s),s);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function di(e,t){return(s,r,i)=>{const o=n=>{var a;return((a=n.renderRoot)==null?void 0:a.querySelector(e))??null};return li(s,r,{get(){return o(this)}})}}class hi{constructor(t="/ws/deep"){this.ws=null,this.handlers=new Set,this.reconnectDelay=1e3,this.maxDelay=15e3,this.closedByUser=!1,this.status="closed";const s=location.protocol==="https:"?"wss":"ws";this.url=`${s}://${location.host}${t}`}connect(){this.closedByUser=!1,this.status="connecting",this.ws=new WebSocket(this.url),this.ws.onopen=()=>{this.status="open",this.reconnectDelay=1e3,this.emit({type:"_socket_open"})},this.ws.onmessage=t=>{try{this.emit(JSON.parse(t.data))}catch{}},this.ws.onclose=()=>{this.status="closed",this.emit({type:"_socket_close"}),this.closedByUser||this.scheduleReconnect()},this.ws.onerror=()=>{var t;return(t=this.ws)==null?void 0:t.close()}}scheduleReconnect(){setTimeout(()=>this.connect(),this.reconnectDelay),this.reconnectDelay=Math.min(this.reconnectDelay*1.6,this.maxDelay)}send(t){var s;((s=this.ws)==null?void 0:s.readyState)===WebSocket.OPEN&&this.ws.send(JSON.stringify(t))}on(t){return this.handlers.add(t),()=>this.handlers.delete(t)}emit(t){for(const s of this.handlers)s(t)}close(){var t;this.closedByUser=!0,(t=this.ws)==null||t.close()}}const ze=new hi;let nt=1;const We=B("closed"),P=B([]),L=B(!1),be=B([]),pi=B("—"),ui=B(""),Rt=B([]),fi=new Set(["ap_left_proximity","persistent_unknown_ap","device_unusual_time","ap_entered_proximity","new_device_detected","network_flow_recorded","device_joined","security_alert"]),at=ts(()=>P.get().some(e=>e.streaming));ts(()=>{const e=L.get(),t=at.get();return We.get()!=="open"?"alert":t?"speaking":e?"thinking":"idle"});function mi(e,t=null){!e.trim()&&!t||(P.set([...P.get(),{id:nt++,role:"user",text:e,image:t}]),L.set(!0),be.set([]),ze.send({type:"chat",text:e,mode:"auto",image:t}))}function vi(){return P.get().find(e=>e.streaming)}function Dt(e){P.set(P.get().map(t=>t.streaming?{...t,...e}:t))}function gi(e){switch(e.type){case"_socket_open":We.set("open");break;case"_socket_close":We.set("closed");break;case"thinking":L.set(!0);break;case"response_start":L.set(!0);break;case"token":{L.set(!1);const t=String(e.content??"");vi()?P.set(P.get().map(r=>r.streaming?{...r,text:r.text+t}:r)):P.set([...P.get(),{id:nt++,role:"ai",text:t,streaming:!0}]);break}case"response_end":{L.set(!1);const t=e;t.model&&pi.set(t.model);const s=be.get();Dt({streaming:!1,model:t.model,latency:t.latency,reasoning:s.length?s:void 0}),be.set([]);break}case"reasoning":{const t=e.step;t&&be.set([...be.get(),t]);break}case"error":{L.set(!1),Dt({streaming:!1}),P.set([...P.get(),{id:nt++,role:"ai",text:`⚠ ${e.message??"error"}`}]);break}default:if(ui.set(e.type),fi.has(e.type)){const t=new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"}),s=e.type.replace(/_/g," ");Rt.set([{time:t,label:s,type:e.type},...Rt.get()].slice(0,40))}}}let Lt=!1;function bi(){Lt||(Lt=!0,ze.on(e=>gi(e)),ze.connect())}async function b(e){const t=await fetch(e);if(!t.ok)throw new Error(`${e} → ${t.status}`);return await t.json()}const yi=(e=!1)=>b(`/api/providers/health${e?"?force=true":""}`),er=()=>b("/api/chem/table"),tr=e=>b(`/api/chem/element/${e}`),sr=()=>b("/api/physics/constants"),ir=e=>b("/api/physics/formulas"),rr=()=>b("/api/vitals"),or=()=>b("/api/system/info"),nr=()=>b("/api/geo/self");async function ar(e){return await(await fetch("/api/math/solve",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({query:e})})).json()}async function cr(e){return await(await fetch("/api/science/compute",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({query:e})})).json()}const lr=(e=1)=>b(`/api/finance/summary?months=${e}`),dr=e=>{const t=new URLSearchParams;return e!=null&&e.start&&t.set("start",e.start),e!=null&&e.end&&t.set("end",e.end),e!=null&&e.category&&t.set("category",e.category),t.set("limit",String(e.limit)),b(`/api/finance/transactions?${t}`)},hr=()=>b("/api/finance/budgets"),pr=(e=14)=>b(`/api/finance/bills/upcoming?days=${e}`),ur=e=>b("/api/finance/anomalies");async function fr(e){return(await fetch("/api/finance/transaction",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(e)})).json()}async function mr(e){return(await fetch("/api/finance/bill",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(e)})).json()}const vr=(e=20)=>b(`/api/email/inbox?limit=${e}`),gr=(e,t=10)=>b(`/api/email/search?q=${encodeURIComponent(e)}&limit=${t}`),br=()=>b("/api/email/awaiting");async function yr(e){return(await fetch("/api/email/send",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(e)})).json()}async function _r(e){return(await fetch("/api/missions",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({goal:e})})).json()}const wr=(e,t=20)=>b(`/api/missions${e?`?status=${e}&limit=${t}`:`?limit=${t}`}`);async function xr(e){return(await fetch(`/api/missions/${e}/cancel`,{method:"POST"})).json()}const $r=()=>b("/api/security/status"),Sr=()=>b("/api/security/devices"),kr=(e=50)=>b(`/api/security/events?limit=${e}`),Cr=(e=24)=>b(`/network/threats?hours=${e}`);async function Ar(e){return(await fetch("/api/security/trust",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({mac:e})})).json()}async function Er(e){return(await fetch("/api/security/block",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({mac:e})})).json()}async function Pr(e){return(await fetch("/api/security/acknowledge",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({event_id:e})})).json()}async function Tr(e){return(await fetch(`/network/scan/${encodeURIComponent(e)}`,{method:"POST"})).json()}const Or=()=>b("/network/wifi"),Mr=e=>b("/api/network/graph"),Nr=()=>b("/api/network/stats"),Ir=(e,t,s=24)=>b(`/api/network/observations/${encodeURIComponent(e)}?hours=${s}`),Rr=(e,t,s=20)=>b(`/api/network/inferences/${encodeURIComponent(e)}?limit=${s}`);async function Dr(e,t){return(await fetch("/api/network/analyse",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({scope:e,node_id:t})})).json()}var _i=Object.defineProperty,wi=Object.getOwnPropertyDescriptor,as=(e,t,s,r)=>{for(var i=r>1?void 0:r?wi(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&_i(t,s,i),i};let xi=0,Me=null;function te(e,t="info",s=6e3){Me||(Me=document.createElement("ds-toast-host"),document.body.appendChild(Me)),Me.push({id:++xi,text:e,kind:t},s)}let je=class extends E{constructor(){super(...arguments),this.items=[]}push(e,t){this.items=[...this.items,e],setTimeout(()=>this.dismiss(e.id),t)}dismiss(e){this.items=this.items.filter(t=>t.id!==e)}render(){return f`${this.items.map(e=>f`
        <div class="toast ${e.kind}">
          <span>${e.text}</span>
          <button class="x" @click=${()=>this.dismiss(e.id)} aria-label="Dismiss">✕</button>
        </div>
      `)}`}};je.styles=H`
    :host {
      position: fixed;
      bottom: var(--ds-space-5);
      right: var(--ds-space-5);
      z-index: var(--ds-z-toast);
      display: flex;
      flex-direction: column;
      gap: var(--ds-space-2);
      max-width: 380px;
    }
    .toast {
      display: flex;
      align-items: center;
      gap: var(--ds-space-3);
      padding: var(--ds-space-3) var(--ds-space-4);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border-strong);
      border-radius: var(--ds-radius-md);
      box-shadow: var(--ds-elev-3);
      font-size: var(--ds-text-sm);
      animation: slide var(--ds-dur-base) var(--ds-ease-spring);
    }
    .info    { border-left: 2px solid var(--ds-info); }
    .success { border-left: 2px solid var(--ds-success); }
    .danger  { border-left: 2px solid var(--ds-danger); }
    .x { margin-left: auto; cursor: pointer; color: var(--ds-text-muted); border: 0; background: none; font-size: var(--ds-text-sm); }
    .x:hover { color: var(--ds-text); }
    @keyframes slide { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: none; } }
  `;as([x()],je.prototype,"items",2);je=as([q("ds-toast-host")],je);const Fe=[];function C(e){Fe.some(t=>t.id===e.id)||Fe.push(e)}function $i(e,t){const s=e.toLowerCase(),r=t.toLowerCase();let i=0,o=0;for(const n of s){const a=r.indexOf(n,i);if(a===-1)return-1;o+=a-i+(a===i?0:2),i=a+1}return o}function Si(e){return e.trim()?Fe.map(t=>({c:t,s:$i(e,t.label)})).filter(t=>t.s>=0).sort((t,s)=>t.s-s.s).map(t=>t.c):Fe}const U=e=>()=>{location.hash=e};C({id:"nav.chat",label:"Go to Chat",hint:"nav",run:U("home")});C({id:"nav.gallery",label:"Open Design Gallery",hint:"nav",run:U("gallery")});C({id:"nav.science",label:"Open Science (Periodic Table & Physics)",hint:"nav",run:U("science")});C({id:"nav.ops",label:"Open Ops (Providers · Security · Knowledge)",hint:"nav",run:U("ops")});C({id:"nav.agents",label:"Open Agents Board",hint:"nav",run:U("agents")});C({id:"nav.memory",label:"Open Memory Graph",hint:"nav",run:U("memory")});C({id:"nav.network",label:"Open Network (Devices · Vitals · Proximity)",hint:"nav",run:U("network")});C({id:"nav.audit",label:"Open Audit Ledger",hint:"nav",run:U("audit")});C({id:"nav.system",label:"Open System Monitor (Usage · Displays · Cores)",hint:"nav",run:U("system")});C({id:"nav.geo",label:"Open Geo Location",hint:"nav",run:U("geo")});C({id:"nav.calc",label:"Open Graphing Calculator",hint:"nav",run:U("calc")});C({id:"nav.legacy",label:"Open Legacy UI (/ai)",hint:"nav",run:()=>{location.href="/ai"}});C({id:"ui.theme",label:"Toggle Theme (Calm ⇄ Neon)",hint:"ui",run:()=>Bs()});C({id:"sys.providers",label:"Check AI Provider Health",hint:"system",run:async()=>{try{const e=await yi(!0),t=e.providers.filter(s=>s.configured&&!s.ok);t.length?te(`${t.length} provider(s) down: ${t.map(s=>s.provider).join(", ")}`,"danger",9e3):te(`All ${e.healthy}/${e.total} provider keys healthy`,"success")}catch{te("Provider health check failed","danger")}}});C({id:"sys.screen",label:"Describe My Screen",hint:"vision",run:async()=>{te("DEEP is looking at your screen…","info");try{const t=await(await fetch("/api/vision/screen",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({q:"Describe what's on this screen for Aryan, concisely."})})).json();t.ok?te(String(t.description).slice(0,280),"success",14e3):te(`Screen read failed: ${t.error}`,"danger")}catch{te("Screen read failed","danger")}}});var ki=Object.defineProperty,Ci=Object.getOwnPropertyDescriptor,Ee=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ci(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&ki(t,s,i),i};let re=class extends E{constructor(){super(...arguments),this.open=!1,this.q="",this.sel=0}show(){this.open=!0,this.q="",this.sel=0,requestAnimationFrame(()=>{var e;return(e=this.input)==null?void 0:e.focus()})}hide(){this.open=!1}toggle(){this.open?this.hide():this.show()}results(){return Si(this.q)}run(e){this.hide(),e.run()}onKey(e){const t=this.results();e.key==="Escape"?this.hide():e.key==="ArrowDown"?(e.preventDefault(),this.sel=Math.min(this.sel+1,t.length-1)):e.key==="ArrowUp"?(e.preventDefault(),this.sel=Math.max(this.sel-1,0)):e.key==="Enter"&&t[this.sel]&&this.run(t[this.sel])}render(){if(!this.open)return f``;const e=this.results();return f`
      <div class="scrim" @click=${t=>{t.target===t.currentTarget&&this.hide()}}>
        <div class="box" role="dialog" aria-modal="true" aria-label="Command palette">
          <input
            placeholder="Type a command…"
            role="combobox"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-label="Search commands"
            .value=${this.q}
            @input=${t=>{this.q=t.target.value,this.sel=0}}
            @keydown=${this.onKey}
          />
          ${e.length?f`<ul role="listbox" aria-label="Commands">
                ${e.map((t,s)=>f`
                    <li class=${s===this.sel?"sel":""}
                        role="option"
                        aria-selected=${s===this.sel}
                        @mouseenter=${()=>this.sel=s}
                        @click=${()=>this.run(t)}>
                      <span>${t.label}</span>
                      ${t.hint?f`<span class="hint">${t.hint}</span>`:""}
                    </li>
                  `)}
              </ul>`:f`<div class="none">No matching commands.</div>`}
        </div>
      </div>
    `}};re.styles=H`
    .scrim {
      position: fixed; inset: 0;
      background: var(--ds-scrim);
      z-index: var(--ds-z-palette);
      display: grid;
      place-items: start center;
      padding-top: 14vh;
      animation: fade var(--ds-dur-fast) var(--ds-ease-out);
    }
    .box {
      width: min(560px, 92vw);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-lg));
      backdrop-filter: blur(var(--ds-blur-lg));
      border: 1px solid var(--ds-border-strong);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-4);
      overflow: hidden;
      animation: pop var(--ds-dur-base) var(--ds-ease-spring);
    }
    input {
      width: 100%;
      padding: var(--ds-space-4);
      border: 0; outline: 0; background: none;
      color: var(--ds-text);
      font-family: var(--ds-font-sans);
      font-size: var(--ds-text-base);
      border-bottom: 1px solid var(--ds-border);
    }
    input::placeholder { color: var(--ds-text-faint); }
    ul { list-style: none; margin: 0; padding: var(--ds-space-2); max-height: 320px; overflow-y: auto; }
    li {
      display: flex; align-items: center; justify-content: space-between;
      padding: var(--ds-space-2) var(--ds-space-3);
      border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-sm);
      cursor: pointer;
      color: var(--ds-text-soft);
    }
    li.sel { background: rgba(var(--ds-periwinkle-rgb), 0.14); color: var(--ds-text); }
    li .hint {
      font-family: var(--ds-font-mono);
      font-size: 0.62rem;
      color: var(--ds-text-faint);
      text-transform: uppercase;
      letter-spacing: var(--ds-tracking-wide);
    }
    .none { padding: var(--ds-space-4); color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
    @keyframes fade { from { opacity: 0; } }
    @keyframes pop { from { opacity: 0; transform: translateY(-8px) scale(0.98); } }
  `;Ee([x()],re.prototype,"open",2);Ee([x()],re.prototype,"q",2);Ee([x()],re.prototype,"sel",2);Ee([di("input")],re.prototype,"input",2);re=Ee([q("command-palette")],re);var Ai=Object.defineProperty,Ei=Object.getOwnPropertyDescriptor,mt=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ei(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Ai(t,s,i),i};let Se=class extends E{constructor(){super(...arguments),this.visible=!0,this.progress=0,this.raf=0,this.start=performance.now(),this._loop=()=>{const e=performance.now()-this.start;if(this.progress=Math.min(100,e/3800*100),e>3500&&e<4e3&&this.classList.add("ready"),e>4e3){this.classList.add("fade"),setTimeout(()=>{this.visible=!1},1e3);return}this.raf=requestAnimationFrame(this._loop)}}connectedCallback(){super.connectedCallback(),this._loop()}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf)}render(){if(!this.visible)return f``;const e=2*Math.PI*66,t=`${e*(this.progress/100)} ${e}`,s=["INITIALISING NEURAL SUBSTRATE...","LOADING KNOWLEDGE GRAPH...","WARMING EMBEDDING MODEL...","CALIBRATING PREDICTIVE ENGINE...","ESTABLISHING SECURE UPLINK...","MOUNTING VOICE INTERFACE...","COALESCING INTELLIGENCE CORE...","SYSTEM READY"],r=Math.min(s.length-1,Math.floor(this.progress/100*s.length));return f`
      <div class="wrap">
        <div class="ring-wrap">
          <svg class="ring-svg" viewBox="0 0 140 140">
            <circle class="ring-track" cx="70" cy="70" r="66" />
            <circle class="ring-fill" cx="70" cy="70" r="66" stroke-dasharray="${t}" />
          </svg>
          <div class="logo"><span class="om">ॐ</span></div>
        </div>
        <div class="tagline">Dynamic · Empathic · Execution · Processor</div>
        <div class="bar-wrap"><div class="bar" style="width:${this.progress}%"></div></div>
        <div class="status">${s[r]}</div>
        <div class="ready-flash"></div>
      </div>
    `}};Se.styles=H`
    :host {
      position: fixed; inset: 0; z-index: 100;
      display: grid; place-items: center;
      background: #000205;
      transition: opacity 1s ease, visibility 1s;
    }
    :host(.fade) { opacity: 0; visibility: hidden; pointer-events: none; }
    .wrap { display: grid; gap: 28px; text-align: center; position: relative; }
    .ring-wrap {
      position: relative;
      width: 140px; height: 140px;
      margin: 0 auto;
      display: grid; place-items: center;
    }
    .ring-svg {
      position: absolute; inset: 0;
      transform: rotate(-90deg);
    }
    .ring-track { fill: none; stroke: rgba(0,229,255,0.06); stroke-width: 2; }
    .ring-fill {
      fill: none; stroke: var(--ds-accent, #00e5ff); stroke-width: 2;
      stroke-linecap: round;
      transition: stroke-dashoffset 0.1s linear;
      filter: drop-shadow(0 0 4px var(--ds-accent, #00e5ff));
    }
    .logo {
      font-size: 2.4rem; font-weight: 700; letter-spacing: 0.12em;
      color: #eaf6ff; text-shadow: 0 0 40px rgba(0,229,255,0.35);
      animation: text-glow 2s ease-in-out infinite;
    }
    .om { color: var(--ds-accent, #00e5ff); margin-right: 8px; }
    .tagline {
      font-size: 0.72rem; letter-spacing: 0.28em; color: rgba(234,246,255,0.45);
      text-transform: uppercase;
    }
    .bar-wrap {
      width: 220px; height: 3px; margin: 8px auto 0;
      background: rgba(0,229,255,0.08); border-radius: 2px; overflow: hidden;
    }
    .bar {
      height: 100%; width: 0%;
      background: linear-gradient(90deg, rgba(0,229,255,0.6), rgba(0,255,209,0.8));
      border-radius: 2px; transition: width 0.1s linear;
      box-shadow: 0 0 12px rgba(0,229,255,0.3);
    }
    .status {
      font-size: 0.65rem; font-family: var(--ds-font-mono, monospace);
      color: rgba(234,246,255,0.35); letter-spacing: 0.08em;
      min-height: 1.2em;
    }
    .ready-flash {
      position: absolute; inset: 0;
      background: radial-gradient(circle at center, rgba(0,229,255,0.15), transparent 60%);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.4s ease;
    }
    :host(.ready) .ready-flash { opacity: 1; }
  `;mt([x()],Se.prototype,"visible",2);mt([x()],Se.prototype,"progress",2);Se=mt([q("deep-boot")],Se);var Pi=Object.defineProperty,Ti=Object.getOwnPropertyDescriptor,cs=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ti(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Pi(t,s,i),i};let Oi=1,He=class extends E{constructor(){super(...arguments),this.toasts=[]}connectedCallback(){super.connectedCallback(),setTimeout(()=>this._push({title:"DEEP Online",body:"Voice assistant connected and ready.",type:"success"}),1200),setTimeout(()=>this._push({title:"Network Scan Complete",body:"24 devices discovered. 1 unknown flagged.",type:"info",action:{label:"Review →",href:"#network"}}),3500)}_push(e){const t={...e,id:Oi++};this.toasts=[...this.toasts,t],setTimeout(()=>this._remove(t.id),6e3)}_remove(e){const t=this.renderRoot.querySelector(`[data-id="${e}"]`);t&&t.classList.add("out"),setTimeout(()=>{this.toasts=this.toasts.filter(s=>s.id!==e)},350)}render(){return f`
      ${this.toasts.map(e=>f`
        <div class="toast ${e.type}" data-id="${e.id}">
          <button class="toast-close" @click=${()=>this._remove(e.id)}>×</button>
          <div class="toast-title">${e.title}</div>
          <div class="toast-body">${e.body}</div>
          ${e.action?f`<a class="toast-action" href="${e.action.href}">${e.action.label}</a>`:""}
        </div>
      `)}
    `}};He.styles=H`
    :host {
      position: fixed;
      top: 16px; right: 16px;
      z-index: 3000;
      display: flex; flex-direction: column;
      gap: 10px;
      max-width: 340px;
      pointer-events: none;
    }
    .toast {
      pointer-events: auto;
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-lg));
      -webkit-backdrop-filter: blur(var(--ds-blur-lg));
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md);
      padding: var(--ds-space-3) var(--ds-space-4);
      box-shadow: var(--ds-elev-3);
      animation: toast-in 0.35s var(--ds-ease-out) both;
      position: relative;
      overflow: hidden;
    }
    .toast.out { animation: toast-out 0.3s var(--ds-ease-out) both; }
    .toast::before {
      content: "";
      position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    }
    .toast.info::before  { background: var(--ds-info); box-shadow: 0 0 6px var(--ds-info); }
    .toast.success::before { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .toast.warn::before  { background: var(--ds-warning); box-shadow: 0 0 6px var(--ds-warning); }
    .toast.alert::before { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .toast-title {
      font-size: var(--ds-text-sm); font-weight: 600;
      color: var(--ds-text-soft);
      margin-bottom: 2px;
    }
    .toast-body {
      font-size: var(--ds-text-xs);
      color: var(--ds-text-muted);
      line-height: 1.4;
    }
    .toast-action {
      margin-top: var(--ds-space-2);
      display: inline-block;
      font-size: var(--ds-text-xs);
      color: var(--ds-accent);
      text-decoration: none;
      font-weight: 500;
      cursor: pointer;
    }
    .toast-action:hover { text-decoration: underline; }
    .toast-close {
      position: absolute; top: 6px; right: 8px;
      background: none; border: none; color: var(--ds-text-faint);
      font-size: 14px; cursor: pointer; line-height: 1;
    }
    .toast-close:hover { color: var(--ds-text); }
  `;cs([x()],He.prototype,"toasts",2);He=cs([q("toast-stack")],He);var Mi=Object.defineProperty,Ni=Object.getOwnPropertyDescriptor,fe=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ni(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Mi(t,s,i),i};let X=class extends E{constructor(){super(...arguments),this.voiceState="IDLE",this.transcript="",this.muted=!1,this.connected=!1,this.ws=null}connectedCallback(){super.connectedCallback(),this._connectWs()}disconnectedCallback(){super.disconnectedCallback(),this.ws&&(this.ws.close(),this.ws=null)}_connectWs(){const t=`${location.protocol==="https:"?"wss:":"ws:"}//${location.host}/ws/voice`;try{this.ws=new WebSocket(t),this.ws.onopen=()=>{this.connected=!0},this.ws.onclose=()=>{this.connected=!1,setTimeout(()=>this._connectWs(),3e3)},this.ws.onmessage=s=>{try{const r=JSON.parse(s.data);r.type==="state"&&r.state&&(this.voiceState=r.state,this.transcript=r.transcript||"")}catch{}}}catch{}}render(){const e=`state-${this.voiceState.toLowerCase()}`,t=this.muted?"muted":"",s=this.connected?"connected":"disconnected",r={IDLE:"DEEP is listening…",WAKE:"Wake detected!",LISTENING:"Listening…",THINKING:"Thinking…",ACTING:"Taking action…",SPEAKING:"Speaking…",COOLDOWN:"Cooling down…",CONFIRMING:"Confirm?",ALERT:"Alert!"},i=this.voiceState==="SPEAKING";return f`
      <div class="wrap ${e} ${t}">
        ${this.transcript?f`
          <div class="transcript-bubble show">
            <div class="state-label">${r[this.voiceState]||this.voiceState}</div>
            <div>${this.transcript}</div>
          </div>
        `:""}
        <div class="orb" @click=${()=>{this.muted=!this.muted}}>
          <div class="connection-dot ${s}"></div>
          <div class="orb-inner"></div>
          ${i?f`
            <div class="waveform">
              <div class="bar" style="height:8px"></div>
              <div class="bar" style="height:14px"></div>
              <div class="bar" style="height:10px"></div>
              <div class="bar" style="height:16px"></div>
              <div class="bar" style="height:12px"></div>
            </div>
          `:""}
          <div class="tooltip">
            <div class="state-label">${r[this.voiceState]||this.voiceState}</div>
            ${this.transcript?f`<div class="transcript">"${this.transcript}"</div>`:""}
            <div class="actions">
              <button @click=${o=>{o.stopPropagation(),this._sendCommand("stop")}}>Stop</button>
              <button @click=${o=>{o.stopPropagation(),this.muted=!this.muted}}>${this.muted?"Unmute":"Mute"}</button>
            </div>
          </div>
        </div>
      </div>
    `}_sendCommand(e){this.ws&&this.ws.readyState===WebSocket.OPEN&&this.ws.send(JSON.stringify({type:"command",command:e}))}};X.styles=H`
    :host { display: block; position: fixed; bottom: 20px; right: 20px; z-index: 9999; }
    .wrap { position: relative; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }

    /* ── Transcript bubble ── */
    .transcript-bubble {
      background: var(--ds-glass);
      backdrop-filter: blur(var(--ds-blur-md));
      border: 1px solid var(--ds-border-accent);
      border-radius: var(--ds-radius-md);
      padding: var(--ds-space-2) var(--ds-space-3);
      font-size: var(--ds-text-sm);
      color: var(--ds-text-soft);
      max-width: 260px;
      word-break: break-word;
      opacity: 0; transform: translateY(8px);
      transition: opacity 0.3s ease, transform 0.3s ease;
      pointer-events: none;
      box-shadow: var(--ds-elev-2);
    }
    .wrap:hover .transcript-bubble,
    .transcript-bubble.show { opacity: 1; transform: translateY(0); }
    .transcript-bubble .state-label {
      font-size: var(--ds-text-xs); color: var(--ds-accent);
      text-transform: uppercase; letter-spacing: var(--ds-tracking-wide);
      font-weight: 600; margin-bottom: 2px;
    }

    /* ── Holographic orb ── */
    .orb {
      width: 56px; height: 56px; border-radius: 50%;
      position: relative; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      background: radial-gradient(circle at 30% 30%, rgba(var(--ds-periwinkle-rgb),0.15), transparent 60%);
    }
    .orb::before {
      content: ""; position: absolute; inset: -2px; border-radius: 50%;
      background: conic-gradient(from 0deg, transparent, var(--ds-accent), var(--ds-iris, #9a8cff), transparent);
      opacity: 0.25;
      animation: spin-slow 4s linear infinite;
      -webkit-mask: radial-gradient(circle, transparent 62%, black 64%);
      mask: radial-gradient(circle, transparent 62%, black 64%);
    }
    .orb::after {
      content: ""; position: absolute; inset: -6px; border-radius: 50%;
      border: 1px solid rgba(var(--ds-periwinkle-rgb), 0.15);
      transition: all 0.4s ease;
    }

    .orb-inner {
      width: 22px; height: 22px; border-radius: 50%;
      background: var(--ds-accent);
      transition: all 0.4s ease;
      box-shadow: 0 0 12px var(--ds-accent);
    }

    /* IDLE — dim breathing pulse */
    .state-idle .orb-inner { opacity: 0.3; }
    .state-idle .orb { animation: breathe 3s ease-in-out infinite; }
    /* WAKE — quick bright pulse */
    .state-wake .orb-inner { opacity: 1; transform: scale(1.3); box-shadow: 0 0 24px var(--ds-accent); }
    .state-wake .orb { animation: wakePulse 0.5s ease-out; }
    @keyframes wakePulse {
      0% { transform: scale(0.8); opacity: 0.5; }
      50% { transform: scale(1.2); opacity: 1; }
      100% { transform: scale(1); opacity: 1; }
    }
    /* LISTENING — expanding rings */
    .state-listening .orb-inner { opacity: 1; width: 26px; height: 26px; background: var(--ds-success); box-shadow: 0 0 24px var(--ds-success); }
    .state-listening .orb { animation: listeningWave 1.2s ease-in-out infinite; }
    @keyframes listeningWave {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.15); }
    }
    .state-listening .orb::after {
      animation: ring-expand 1.5s ease-out infinite;
      border-color: var(--ds-success);
    }
    /* THINKING — chaotic spin + color cycle */
    .state-thinking .orb-inner {
      opacity: 1; animation: thinkCycle 0.8s linear infinite;
      background: linear-gradient(90deg, var(--ds-accent), var(--ds-success), var(--ds-warning), var(--ds-accent));
      background-size: 300% 100%;
      box-shadow: 0 0 20px var(--ds-accent);
    }
    @keyframes thinkCycle {
      0% { background-position: 0% 50%; }
      100% { background-position: 300% 50%; }
    }
    .state-thinking .orb { animation: spin-slow 2s linear infinite; }
    .state-thinking .orb::before { opacity: 0.5; animation-duration: 1s; }
    /* ACTING — strobes */
    .state-acting .orb-inner { opacity: 1; animation: actStrobe 0.3s ease-in-out infinite alternate; box-shadow: 0 0 20px var(--ds-accent); }
    @keyframes actStrobe {
      0% { opacity: 0.6; transform: scale(1); }
      100% { opacity: 1; transform: scale(1.2); }
    }
    /* SPEAKING — waveform bars */
    .state-speaking .orb-inner { opacity: 0; width: 0; height: 0; }
    .state-speaking .waveform {
      display: flex; align-items: flex-end; gap: 2px;
      height: 20px;
    }
    .waveform .bar {
      width: 3px; border-radius: 2px;
      background: var(--ds-accent);
      animation: bar-bounce 0.5s ease-in-out infinite alternate;
      box-shadow: 0 0 4px var(--ds-accent);
    }
    .waveform .bar:nth-child(2) { animation-delay: 0.08s; height: 14px; }
    .waveform .bar:nth-child(3) { animation-delay: 0.16s; height: 10px; }
    .waveform .bar:nth-child(4) { animation-delay: 0.12s; height: 16px; }
    .waveform .bar:nth-child(5) { animation-delay: 0.04s; height: 12px; }
    .state-speaking .orb::after { border-color: var(--ds-accent); animation: ring-expand 1.2s ease-out infinite; }
    /* COOLDOWN — gentle fade */
    .state-cooldown .orb-inner { opacity: 0.5; transform: scale(0.9); }
    /* CONFIRMING — amber slow pulse */
    .state-confirming .orb-inner { background: var(--ds-warning); opacity: 1; box-shadow: 0 0 20px var(--ds-warning); }
    .state-confirming .orb { animation: confirmPulse 1.5s ease-in-out infinite; }
    @keyframes confirmPulse {
      0%, 100% { transform: scale(1); opacity: 0.8; }
      50% { transform: scale(1.12); opacity: 1; }
    }
    /* ALERT — red flashes */
    .state-alert .orb-inner { background: var(--ds-danger); opacity: 1; box-shadow: 0 0 24px var(--ds-danger); }
    .state-alert .orb { animation: alertFlash 0.4s ease-in-out 3; }
    @keyframes alertFlash {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.3; transform: scale(1.3); }
    }
    /* Muted overlay */
    .muted .orb-inner { background: var(--ds-text-faint) !important; opacity: 0.3 !important; box-shadow: none !important; }
    .muted .orb { animation: none !important; }
    .muted .waveform { display: none !important; }

    /* Tooltip */
    .tooltip {
      position: absolute; bottom: 68px; right: 0;
      background: var(--ds-surface-1); border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md); padding: var(--ds-space-3);
      min-width: 220px; font-size: var(--ds-text-sm);
      color: var(--ds-text); box-shadow: var(--ds-elev-3);
      opacity: 0; transform: translateY(8px); pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    .orb:hover .tooltip, .tooltip.show {
      opacity: 1; transform: translateY(0); pointer-events: auto;
    }
    .tooltip .state-label { font-size: var(--ds-text-xs); color: var(--ds-accent); text-transform: uppercase; letter-spacing: var(--ds-tracking-wide); font-weight: 600; }
    .tooltip .transcript { color: var(--ds-text-muted); margin-top: var(--ds-space-1); font-style: italic; max-width: 260px; word-break: break-word; }
    .tooltip .actions { display: flex; gap: var(--ds-space-2); margin-top: var(--ds-space-2); }
    .tooltip .actions button {
      background: var(--ds-surface-2); border: 1px solid var(--ds-border);
      color: var(--ds-text); padding: 2px 10px; border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-xs); cursor: pointer;
    }
    .tooltip .actions button:hover { background: var(--ds-surface-3); }
    .connection-dot { position: absolute; top: 2px; right: 2px; width: 8px; height: 8px; border-radius: 50%; }
    .connection-dot.connected { background: var(--ds-success); box-shadow: 0 0 4px var(--ds-success); }
    .connection-dot.disconnected { background: var(--ds-danger); }
  `;fe([x()],X.prototype,"voiceState",2);fe([x()],X.prototype,"transcript",2);fe([x()],X.prototype,"muted",2);fe([x()],X.prototype,"connected",2);fe([x()],X.prototype,"ws",2);X=fe([q("voice-status-orb")],X);var Ii=Object.defineProperty,Ri=Object.getOwnPropertyDescriptor,vt=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ri(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Ii(t,s,i),i};const Ut={idle:[0,1,.53],active:[0,.9,1],speaking:[1,0,.67],thinking:[1,.67,0],warning:[1,.2,.2],indexing:[.67,.4,1]},Di=`#version 300 es
in vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }`,Li=`#version 300 es
precision highp float;
out vec4 o;
uniform vec2  u_res;
uniform float u_time;
uniform float u_activity;   // 0..1
uniform vec3  u_accent;     // status colour
uniform vec2  u_mouse;      // 0..1

float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  float a = hash(i), b = hash(i+vec2(1.,0.)), c = hash(i+vec2(0.,1.)), d = hash(i+vec2(1.,1.));
  vec2 u = f*f*(3.-2.*f);
  return mix(mix(a,b,u.x), mix(c,d,u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for(int i=0;i<5;i++){ v += a*noise(p); p *= 2.0; a *= 0.5; }
  return v;
}
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 c = (gl_FragCoord.xy - 0.5*u_res) / u_res.y;  // aspect-correct, centered

  // Flowing nebula
  float t = u_time * 0.04;
  vec2 q = c*1.6 + vec2(t, -t*0.6);
  float n = fbm(q + fbm(q + t));
  vec3 neb = mix(vec3(0.02,0.03,0.06), u_accent*0.5, smoothstep(0.35,0.85,n)) * (0.35 + 0.4*u_activity);

  // Holographic grid (perspective-ish), subtle
  vec2 g = abs(fract(uv*vec2(40.0,24.0)) - 0.5);
  float grid = smoothstep(0.48,0.5, max(g.x,g.y));
  neb += u_accent * grid * 0.04;

  // Radial glow from center, pulses with activity
  float r = length(c);
  float pulse = 0.5 + 0.5*sin(u_time*1.5);
  float glow = exp(-r*2.4) * (0.12 + 0.5*u_activity*pulse);
  neb += u_accent * glow;

  // Mouse-proximity highlight
  float md = length(c - (u_mouse-0.5)*vec2(u_res.x/u_res.y, -1.0)*2.0);
  neb += u_accent * exp(-md*5.0) * 0.15;

  // Scanlines + vignette
  neb *= 1.0 - 0.06*sin(gl_FragCoord.y*1.5);
  neb *= smoothstep(1.25, 0.2, r);

  o = vec4(neb, 1.0);
}`;let ke=class extends E{constructor(){super(...arguments),this.activity=0,this.status="idle",this.backend="none",this.gl=null,this.prog=null,this.uni={},this.raf=0,this.lastDraw=0,this.dpr=1,this.reduced=!1,this.mouse={x:.5,y:.5},this.start=performance.now(),this._onMouse=e=>{this.mouse.x=e.clientX/window.innerWidth,this.mouse.y=e.clientY/window.innerHeight},this._resize=()=>{if(!this.canvas||!this.gl)return;const e=Math.floor(this.canvas.clientWidth*this.dpr),t=Math.floor(this.canvas.clientHeight*this.dpr);this.canvas.width=e,this.canvas.height=t,this.gl.viewport(0,0,e,t)},this._loop=e=>{this.raf=requestAnimationFrame(this._loop);const t=this.activity>=.5?0:this.activity>.1?33:100;e-this.lastDraw<t||(this.lastDraw=e,this._draw(e))}}connectedCallback(){super.connectedCallback(),this.reduced=matchMedia("(prefers-reduced-motion: reduce)").matches,window.addEventListener("mousemove",this._onMouse,{passive:!0}),window.addEventListener("resize",this._resize)}disconnectedCallback(){super.disconnectedCallback(),cancelAnimationFrame(this.raf),window.removeEventListener("mousemove",this._onMouse),window.removeEventListener("resize",this._resize)}firstUpdated(){this.canvas=this.renderRoot.querySelector("canvas"),this.dpr=Math.min(window.devicePixelRatio||1,1.5),this.backend=this._detect();let e=!1;try{this.backend==="webgl2"&&(e=this._initWebGL2())}catch{e=!1}if(!e){this._die();return}this._resize(),this.reduced?this._draw(performance.now()):this.raf=requestAnimationFrame(this._loop)}_detect(){const e="gpu"in navigator&&!!navigator.gpu,t=document.createElement("canvas").getContext("webgl2");return e&&t||t?"webgl2":"canvas"}_die(){this.classList.add("dead"),cancelAnimationFrame(this.raf)}_compile(e,t){const s=this.gl,r=s.createShader(e);if(s.shaderSource(r,t),s.compileShader(r),!s.getShaderParameter(r,s.COMPILE_STATUS)){const i=s.getShaderInfoLog(r);throw s.deleteShader(r),new Error("shader compile failed: "+i)}return r}_initWebGL2(){const e=this.canvas.getContext("webgl2",{antialias:!1,alpha:!1,premultipliedAlpha:!1});if(!e)return!1;this.gl=e;const t=e.createProgram();if(e.attachShader(t,this._compile(e.VERTEX_SHADER,Di)),e.attachShader(t,this._compile(e.FRAGMENT_SHADER,Li)),e.linkProgram(t),!e.getProgramParameter(t,e.LINK_STATUS))throw new Error("program link failed: "+e.getProgramInfoLog(t));this.prog=t,e.useProgram(t);const s=e.createBuffer();e.bindBuffer(e.ARRAY_BUFFER,s),e.bufferData(e.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),e.STATIC_DRAW);const r=e.getAttribLocation(t,"p");e.enableVertexAttribArray(r),e.vertexAttribPointer(r,2,e.FLOAT,!1,0,0);for(const i of["u_res","u_time","u_activity","u_accent","u_mouse"])this.uni[i]=e.getUniformLocation(t,i);return!0}_draw(e){const t=this.gl;if(!t||!this.prog)return;t.useProgram(this.prog);const s=Ut[this.status]??Ut.idle;t.uniform2f(this.uni.u_res,this.canvas.width,this.canvas.height),t.uniform1f(this.uni.u_time,(e-this.start)/1e3),t.uniform1f(this.uni.u_activity,Math.max(0,Math.min(1,this.activity))),t.uniform3f(this.uni.u_accent,s[0],s[1],s[2]),t.uniform2f(this.uni.u_mouse,this.mouse.x,this.mouse.y),t.drawArrays(t.TRIANGLES,0,3)}render(){return f`<canvas></canvas>`}};ke.styles=H`
    :host { display: block; position: fixed; inset: 0; z-index: -1; pointer-events: none; }
    canvas { width: 100%; height: 100%; display: block; }
    :host(.dead) { display: none; }   /* fail-soft: let the HUD/CSS show */
  `;vt([V({attribute:!1})],ke.prototype,"activity",2);vt([V({attribute:!1})],ke.prototype,"status",2);ke=vt([q("deep-shader-bg")],ke);const ls=[{id:"agents",label:"Agents",icon:"✦",group:"intelligence",load:()=>A(()=>import("./agents-view-DxoeWgt8.js"),__vite__mapDeps([0,1,2])),render:()=>f`<agents-view></agents-view>`},{id:"memory",label:"Knowledge",icon:"◐",group:"intelligence",load:()=>A(()=>import("./memory-graph-CGk_U06o.js"),[]),render:()=>f`<memory-graph></memory-graph>`},{id:"research",label:"Research",icon:"◑",group:"intelligence",load:()=>A(()=>import("./research-view-BG3oOpgp.js"),__vite__mapDeps([3,1,2])),render:()=>f`<research-view></research-view>`},{id:"science",label:"Science",icon:"∿",group:"intelligence",load:()=>A(()=>import("./science-view-Bn0GBYGI.js"),__vite__mapDeps([4,5,1])),render:()=>f`<science-view></science-view>`},{id:"calc",label:"Compute",icon:"∑",group:"intelligence",load:()=>A(()=>import("./calc-view-DASy92gl.js"),__vite__mapDeps([6,5,1,2])),render:()=>f`<calc-view></calc-view>`},{id:"missions",label:"Missions",icon:"➤",group:"intelligence",load:()=>A(()=>import("./missions-view-BTJznA1X.js"),__vite__mapDeps([7,1,2])),render:()=>f`<missions-view></missions-view>`},{id:"network",label:"Network",icon:"◎",group:"system",load:()=>A(()=>import("./network-view-BYibjHQw.js"),__vite__mapDeps([8,1,2])),render:()=>f`<network-view></network-view>`},{id:"etis",label:"ETIS",icon:"🛡",group:"system",load:()=>A(()=>import("./etis-hud-DvIJLd5L.js"),__vite__mapDeps([9,1,2])),render:()=>f`<etis-hud></etis-hud>`},{id:"system",label:"System",icon:"▦",group:"system",load:()=>A(()=>import("./system-monitor-BhQ5iErD.js"),__vite__mapDeps([10,1])),render:()=>f`<system-monitor></system-monitor>`},{id:"geo",label:"Geo",icon:"✣",group:"system",load:()=>A(()=>import("./geo-view-DEpC7TJh.js"),__vite__mapDeps([11,1])),render:()=>f`<geo-view></geo-view>`},{id:"audit",label:"Audit",icon:"❖",group:"system",load:()=>A(()=>import("./audit-view-BuOe0SoZ.js"),__vite__mapDeps([12,1])),render:()=>f`<audit-view></audit-view>`},{id:"finance",label:"Finance",icon:"₿",group:"personal",load:()=>A(()=>import("./finance-view-CYWrJXd7.js"),__vite__mapDeps([13,1,2])),render:()=>f`<finance-view></finance-view>`},{id:"email",label:"Email",icon:"✉",group:"personal",load:()=>A(()=>import("./email-view-CU2o6-X2.js"),__vite__mapDeps([14,1,2])),render:()=>f`<email-view></email-view>`},{id:"projects",label:"Projects",icon:"◇",group:"personal",load:()=>A(()=>import("./projects-view-BWOaguFa.js"),__vite__mapDeps([15,1,2])),render:()=>f`<projects-view></projects-view>`}];function zt(e){return ls.find(t=>t.id===e)}class Ui{constructor(){this.ctx=null,this.analyser=null,this.data=new Uint8Array(0),this.smoothBass=0,this.smoothMid=0,this.smoothHigh=0,this.smoothRms=0,this.levels={bass:0,mid:0,high:0,rms:0},this.connected=!1}ensureCtx(){return this.ctx||(this.ctx=new AudioContext,this.analyser=this.ctx.createAnalyser(),this.analyser.fftSize=256,this.analyser.smoothingTimeConstant=.7,this.data=new Uint8Array(this.analyser.frequencyBinCount)),this.ctx}async connectMic(){try{const t=this.ensureCtx();t.state==="suspended"&&await t.resume();const s=await navigator.mediaDevices.getUserMedia({audio:!0});return t.createMediaStreamSource(s).connect(this.analyser),this.connected=!0,!0}catch{return!1}}connectElement(t){try{const s=this.ensureCtx();s.createMediaElementSource(t).connect(this.analyser),this.analyser.connect(s.destination),this.connected=!0}catch{}}update(){if(!this.analyser)return;this.analyser.getByteFrequencyData(this.data);const t=this.data.length;let s=0,r=0,i=0,o=0;const n=6,a=36;for(let g=0;g<t;g++){const y=this.data[g]/255;o+=y,g<n?s+=y:g<a?r+=y:i+=y}const c=Math.min(1,s/n),l=Math.min(1,r/(a-n)),h=Math.min(1,i/Math.max(1,t-a)),d=Math.min(1,o/t*2.5),p=.82;this.smoothBass=this.smoothBass*p+c*(1-p),this.smoothMid=this.smoothMid*p+l*(1-p),this.smoothHigh=this.smoothHigh*p+h*(1-p),this.smoothRms=this.smoothRms*p+d*(1-p),this.levels.bass=this.smoothBass,this.levels.mid=this.smoothMid,this.levels.high=this.smoothHigh,this.levels.rms=this.smoothRms}destroy(){this.ctx&&(this.ctx.close().catch(()=>{}),this.ctx=null,this.analyser=null),this.connected=!1}}let st=null;function Re(){if(st)return st;let e="high";try{const t=navigator,s=t.hardwareConcurrency??8,r=t.deviceMemory??8,i=matchMedia("(pointer: coarse)").matches,o=matchMedia("(prefers-reduced-motion: reduce)").matches;s<=2||r<=2||o?e="low":(s<=4||r<=4||i)&&(e="medium")}catch{}return st=e,e}function zi(){const e=Re();return e==="low"?40:e==="medium"?80:160}let ve=null;function Wi(){if(ve!==null)return ve;try{const e=document.createElement("canvas").getContext("2d");e.filter="blur(1px)",ve=e.filter==="blur(1px)"}catch{ve=!1}return ve}var ji=Object.defineProperty,Fi=Object.getOwnPropertyDescriptor,Pe=(e,t,s,r)=>{for(var i=r>1?void 0:r?Fi(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&ji(t,s,i),i};const le=26,T=46,j=le*T,ge={idle:{noiseFreq:1.7,noiseOctaves:3,noiseAmp:.15,timeSpeed:.15,rotSpeed:.001,lineWidth:.7,particleSpeed:1,hueShift:212,rimPower:2.8},thinking:{noiseFreq:2.8,noiseOctaves:4,noiseAmp:.28,timeSpeed:.5,rotSpeed:.004,lineWidth:.6,particleSpeed:2.5,hueShift:280,rimPower:2},speaking:{noiseFreq:1.4,noiseOctaves:3,noiseAmp:.22,timeSpeed:.3,rotSpeed:.002,lineWidth:1,particleSpeed:1.5,hueShift:35,rimPower:3.2},active:{noiseFreq:2,noiseOctaves:3,noiseAmp:.2,timeSpeed:.35,rotSpeed:.003,lineWidth:.8,particleSpeed:1.8,hueShift:190,rimPower:2.5},warning:{noiseFreq:3.5,noiseOctaves:2,noiseAmp:.35,timeSpeed:.7,rotSpeed:.006,lineWidth:.5,particleSpeed:3,hueShift:0,rimPower:1.5},indexing:{noiseFreq:2.2,noiseOctaves:3,noiseAmp:.18,timeSpeed:.25,rotSpeed:.002,lineWidth:.7,particleSpeed:1.3,hueShift:270,rimPower:2.8}},Hi={idle:190,active:190,speaking:35,thinking:280,warning:0,indexing:270},qi=(e,t,s)=>e+(t-e)*s,Wt=(e,t,s)=>{const r=Math.max(0,Math.min(1,(s-e)/(t-e)));return r*r*(3-2*r)},Vi=e=>e<.5?4*e*e*e:1-Math.pow(-2*e+2,3)/2;let oe=class extends E{constructor(){super(...arguments),this.activity=0,this.status="idle",this.micLevels=null,this.ttsLevels=null,this.raf=0,this.dpr=1,this.reduced=!1,this.filterOk=!0,this.lastDraw=0,this.lastTs=0,this.w=0,this.h=0,this.gw=0,this.gh=0,this.dirs=new Float32Array(0),this.particles=[],this.perm=new Uint8Array(512),this.rot=0,this._prevProfile={...ge.idle},this._currentProfile={...ge.idle},this._targetProfile={...ge.idle},this._transProgress=1,this._transDuration=400,this.ripples=[],this.mx=0,this.my=0,this._smoothMx=0,this._smoothMy=0,this._mouseVelX=0,this._mouseVelY=0,this._prevMx=0,this._prevMy=0,this._ptrDownTime=0,this._ptrDownPos={x:0,y:0},this._clickCount=0,this._clickTimer=0,this._effectiveTier="high",this._frameTimes=[],this.voicePhase=0,this._debug=!1,this._lastFrameMs=0,this._hotCount=0,this.SX=new Float32Array(j),this.SY=new Float32Array(j),this.SZ=new Float32Array(j),this.HU=new Float32Array(j),this.RIM=new Float32Array(j),this.DISP=new Float32Array(j),this._onMouse=e=>{this.mx=(e.clientX/window.innerWidth-.5)*2,this.my=(e.clientY/window.innerHeight-.5)*2},this._onPtrDown=e=>{this._ptrDownTime=performance.now(),this._ptrDownPos={x:e.offsetX,y:e.offsetY}},this._onPtrUp=e=>{const t=performance.now()-this._ptrDownTime;if(!(Math.hypot(e.offsetX-this._ptrDownPos.x,e.offsetY-this._ptrDownPos.y)>20)){if(t>400){this.dispatchEvent(new CustomEvent("sphere-listen",{bubbles:!0,composed:!0})),this.triggerRipple({dx:0,dy:-1,dz:0},2,150,.9);return}this._clickCount++,clearTimeout(this._clickTimer),this._clickTimer=window.setTimeout(()=>{this._clickCount>=2?this.dispatchEvent(new CustomEvent("sphere-command",{bubbles:!0,composed:!0})):(this.dispatchEvent(new CustomEvent("sphere-activate",{bubbles:!0,composed:!0})),this.triggerRipple({dx:0,dy:0,dz:1},4,0,1.2)),this._clickCount=0},250)}},this._resize=()=>{if(!this.canvas||(this.w=this.clientWidth||this.offsetWidth||this.canvas.clientWidth,this.h=this.clientHeight||this.offsetHeight||this.canvas.clientHeight,!this.w||!this.h))return;const e=this.w*this.dpr,t=this.h*this.dpr;this.canvas.width=e,this.canvas.height=t,this.ctx.setTransform(this.dpr,0,0,this.dpr,0,0),this.gw=Math.ceil(this.w/2),this.gh=Math.ceil(this.h/2),this.glow.width=Math.ceil(e/2),this.glow.height=Math.ceil(t/2),this.gctx.setTransform(this.dpr,0,0,this.dpr,0,0)},this._loop=e=>{if(this.raf=requestAnimationFrame(this._loop),(!this.w||!this.h)&&(this._resize(),!this.w||!this.h))return;const t=e-this.lastTs;this.lastTs=e;const s=this.activity>=.5||this.ripples.length?0:this.activity>.1?33:50;if(e-this.lastDraw<s)return;this.lastDraw=e;const r=performance.now();this._updateState(t),this._draw(e),this._measureFrame(r)}}connectedCallback(){super.connectedCallback(),this.reduced=matchMedia("(prefers-reduced-motion: reduce)").matches,this.filterOk=Wi(),this._effectiveTier=Re(),this._debug=new URLSearchParams(location.search).has("debug"),window.addEventListener("mousemove",this._onMouse,{passive:!0})}disconnectedCallback(){var e;super.disconnectedCallback(),cancelAnimationFrame(this.raf),(e=this._ro)==null||e.disconnect(),window.removeEventListener("mousemove",this._onMouse)}updated(e){e.has("status")&&(this._prevProfile={...this._currentProfile},this._targetProfile=ge[this.status]??ge.idle,this._transProgress=0,this.status==="speaking"||this.status==="active"?this.triggerRipple({dx:0,dy:0,dz:1},2,0,1):this.status==="warning"&&this.triggerRipple({dx:0,dy:1,dz:0},3,0,1))}triggerRipple(e,t=2,s=0,r=1){const i=this._effectiveTier==="low"?1:this._effectiveTier==="medium"?3:6;this.ripples.length>=i&&this.ripples.shift(),this.ripples.push({age:0,life:1.6,origin:e,speed:t,color:s,intensity:r})}pulse(){this.triggerRipple({dx:0,dy:0,dz:1},2,0,.8)}firstUpdated(){this.canvas=this.renderRoot.querySelector("canvas"),this.ctx=this.canvas.getContext("2d"),this.glow=document.createElement("canvas"),this.gctx=this.glow.getContext("2d"),this.dpr=Math.min(window.devicePixelRatio||1,2),this._seedGrid(),this._seedNoise(),this._seedParticles(),this.canvas.addEventListener("pointerdown",this._onPtrDown),this.canvas.addEventListener("pointerup",this._onPtrUp),this._ro=new ResizeObserver(()=>this._resize()),this._ro.observe(this),this.reduced||(this.lastTs=performance.now(),this.raf=requestAnimationFrame(this._loop))}_seedGrid(){this.dirs=new Float32Array(j*3);let e=0;for(let t=0;t<le;t++){const s=t/(le-1)*Math.PI,r=Math.sin(s),i=Math.cos(s);for(let o=0;o<T;o++){const n=o/T*Math.PI*2;this.dirs[e++]=r*Math.cos(n),this.dirs[e++]=i,this.dirs[e++]=r*Math.sin(n)}}}_seedNoise(){const e=new Uint8Array(256);for(let t=0;t<256;t++)e[t]=t;for(let t=255;t>0;t--){const s=Math.random()*(t+1)|0;[e[t],e[s]]=[e[s],e[t]]}for(let t=0;t<512;t++)this.perm[t]=e[t&255]}_seedParticles(){const e=zi();this.particles=Array.from({length:e},()=>({x:(Math.random()-.5)*2.4,y:(Math.random()-.5)*2.4,z:(Math.random()-.5)*2.4,vx:(Math.random()-.5)*.002,vy:(Math.random()-.5)*.002}))}_n3(e,t,s){const r=this.perm,i=Math.floor(e)&255,o=Math.floor(t)&255,n=Math.floor(s)&255,a=e-Math.floor(e),c=t-Math.floor(t),l=s-Math.floor(s),h=a*a*(3-2*a),d=c*c*(3-2*c),p=l*l*(3-2*l),g=(ae,W,Te)=>r[r[r[ae&255]+W&255]+Te&255]/255,y=g(i,o,n),O=g(i+1,o,n),M=g(i,o+1,n),N=g(i+1,o+1,n),z=g(i,o,n+1),m=g(i+1,o,n+1),v=g(i,o+1,n+1),u=g(i+1,o+1,n+1),_=y+(O-y)*h,k=M+(N-M)*h,I=z+(m-z)*h,R=v+(u-v)*h,Z=_+(k-_)*d,ne=I+(R-I)*d;return Z+(ne-Z)*p}_fbm(e,t,s,r){let i=0,o=.5;for(let n=0;n<r;n++)i+=o*this._n3(e,t,s),e*=2.03,t*=2.03,s*=2.03,o*=.5;return i}_synthVoice(e){return this.status==="speaking"?(this.voicePhase+=.25,.45+.4*Math.abs(Math.sin(this.voicePhase)*Math.sin(this.voicePhase*.37+1))):this.status==="active"?.15+.1*Math.abs(Math.sin(e*6)):0}_updateState(e){if(this._transProgress<1){this._transProgress=Math.min(1,this._transProgress+e/this._transDuration);const s=Vi(this._transProgress),r=this._currentProfile,i=this._prevProfile,o=this._targetProfile;for(const n of Object.keys(this._currentProfile))r[n]=qi(i[n],o[n],s)}const t=1-Math.pow(.05,e/16);this._smoothMx+=(this.mx-this._smoothMx)*t,this._smoothMy+=(this.my-this._smoothMy)*t,this._mouseVelX=(this.mx-this._prevMx)/Math.max(e,1),this._mouseVelY=(this.my-this._prevMy)/Math.max(e,1),this._prevMx=this.mx,this._prevMy=this.my;for(const s of this.ripples)s.age+=e*.001;this.ripples=this.ripples.filter(s=>s.age<s.life)}_draw(e){const t=this.ctx,s=this.gctx;if(!t||!s)return;const r=this.w,i=this.h,o=e/1e3,n=r/2,a=i/2,c=Math.min(r,i)*.34,l=this._currentProfile,h=this._effectiveTier,d=this.micLevels??this.ttsLevels,p=d?d.bass:this._synthVoice(o),g=d?d.mid:this.status==="thinking"?.4:0,y=d?d.high:0,O=Math.min(1,this.activity+p);this.rot+=l.rotSpeed+O*.002+g*.002;const M=Math.sin(this.rot+this._smoothMx*.5),N=Math.cos(this.rot+this._smoothMx*.5),z=.35+this._smoothMy*.3,m=Math.sin(z),v=Math.cos(z),u=l.noiseAmp+p*.15,_=l.noiseFreq,k=h==="low"?Math.min(l.noiseOctaves,2):h==="medium"?Math.min(l.noiseOctaves,3):l.noiseOctaves,I=l.timeSpeed,R=Math.hypot(this._smoothMx,-this._smoothMy,1.2),Z=this._smoothMx/R,ne=-this._smoothMy/R,ae=1.2/R,W=Math.hypot(this._mouseVelX,this._mouseVelY);this._computeVertices(o,I,_,u,k,n,a,c,M,N,m,v,Z,ne,ae,W),t.clearRect(0,0,r,i),s.clearRect(0,0,this.gw,this.gh),this._renderMesh(s,l,h,o),this._renderRim(s,h,o),this._renderHotSpots(s,h),this._renderParticles(s,l,n/2,a/2,c/2,M,N,m,v),this._renderBackdrop(t,n,a,c,O,l.hueShift),this._compositeBloom(t,r,i,O,h),this._compositeCrisp(t,r,i),this._renderCursorGlow(t,n,a,c,l.hueShift),this._toneClamp(t,r,i),this._debug&&this._renderDebug(t,p,g,y)}_computeVertices(e,t,s,r,i,o,n,a,c,l,h,d,p,g,y,O){const M=o/2,N=n/2,z=a/2;for(let m=0;m<j;m++){const v=this.dirs[m*3],u=this.dirs[m*3+1],_=this.dirs[m*3+2];let k=1+r*(this._fbm(v*s+e*t,u*s,_*s-e*t*.7,i)-.5)*2;for(const D of this.ripples){const ps=v*D.origin.dx+u*D.origin.dy+_*D.origin.dz,yt=Math.acos(Math.max(-1,Math.min(1,ps))),_t=D.age*D.speed,us=Math.exp(-((yt-_t)**2)/.04)*D.intensity,fs=Math.exp(-((yt-_t*.7)**2)/.12)*D.intensity*.4;k+=(us+fs)*.2*(1-D.age/D.life)}const I=v*p+u*g+_*y;if(I>.55){const D=(I-.55)*(.6+O*2);k-=D*.35}else I>.3&&(k+=(I-.3)*.12);this.DISP[m]=k;const R=v*k,Z=u*k,ne=_*k;let ae=R*l-ne*c,W=R*c+ne*l,Te=Z*d-W*h;W=Z*h+W*d;const bt=1/(2-W);this.SX[m]=M+ae*z*bt*2.2,this.SY[m]=N+Te*z*bt*2.2,this.SZ[m]=W,this.HU[m]=this._currentProfile.hueShift+(ae+1)/2*110+16*Math.sin(e*.4+Te*1.8);const hs=Math.abs(W);this.RIM[m]=Math.pow(1-Math.min(1,hs/.55),this._currentProfile.rimPower)}}_renderMesh(e,t,s,r){e.globalCompositeOperation="lighter";for(let i=0;i<le;i++)for(let o=0;o<T;o++){const n=i*T+o,a=i*T+(o+1)%T,c=(i+1)*T+o,l=Wt(-.6,.05,this.SZ[n]),h=.03+l*l*.5+this.RIM[n]*.3,d=(.3+l*.5)*t.lineWidth;e.lineWidth=d,e.strokeStyle=`hsla(${this.HU[n]},95%,${50+l*30+this.RIM[n]*12}%,${h})`,e.beginPath(),e.moveTo(this.SX[n],this.SY[n]),e.lineTo(this.SX[a],this.SY[a]),e.stroke(),i<le-1&&(e.beginPath(),e.moveTo(this.SX[n],this.SY[n]),e.lineTo(this.SX[c],this.SY[c]),e.stroke())}for(let i=0;i<j;i++){const o=Wt(-.6,.05,this.SZ[i]);if(o<.1&&this.RIM[i]<.4)continue;const n=(.3+o*1.2+this.RIM[i]*1)*(s==="low"?.7:1);e.beginPath(),e.arc(this.SX[i],this.SY[i],n,0,Math.PI*2),e.fillStyle=`hsla(${this.HU[i]},100%,${65+o*25}%,${.2+o*.5+this.RIM[i]*.3})`,e.fill()}e.globalCompositeOperation="source-over"}_renderRim(e,t,s){if(t==="low")return;const r=Hi[this.status]??190;e.globalCompositeOperation="lighter",e.lineWidth=1.8;for(let i=0;i<le;i++)for(let o=0;o<T;o++){const n=i*T+o;if(this.RIM[n]<.55)continue;const a=i*T+(o+1)%T;if(this.RIM[a]<.45)continue;const c=.7+.3*Math.sin(s*3.5+n*.08),l=r+55+55*Math.sin(s*.5+n*.11);e.strokeStyle=`hsla(${l},100%,82%,${this.RIM[n]*.7*c})`,e.beginPath(),e.moveTo(this.SX[n],this.SY[n]),e.lineTo(this.SX[a],this.SY[a]),e.stroke()}e.globalCompositeOperation="source-over"}_renderHotSpots(e,t){if(t!=="high"){this._hotCount=0;return}const s=1.18,r=12;let i=0;e.globalCompositeOperation="lighter";for(let o=0;o<j&&i<r;o++){if(this.DISP[o]<s||this.SZ[o]<-.3)continue;i++;const n=Math.min(1,(this.DISP[o]-s)/.25),a=4+n*5,c=e.createRadialGradient(this.SX[o],this.SY[o],0,this.SX[o],this.SY[o],a);c.addColorStop(0,`hsla(${280+n*80},100%,75%,${.5*n})`),c.addColorStop(1,`hsla(${280+n*80},100%,60%,0)`),e.fillStyle=c,e.fillRect(this.SX[o]-a,this.SY[o]-a,a*2,a*2)}e.globalCompositeOperation="source-over",this._hotCount=i}_renderParticles(e,t,s,r,i,o,n,a,c){const l=t.particleSpeed;e.globalCompositeOperation="lighter";for(const h of this.particles){h.x+=h.vx*l,h.y+=h.vy*l,(h.x<-1.4||h.x>1.4)&&(h.vx*=-1),(h.y<-1.4||h.y>1.4)&&(h.vy*=-1);let d=h.x*n-h.z*o,p=h.x*o+h.z*n,g=h.y*c-p*a;p=h.y*a+p*c;const y=1/(2-p),O=s+d*i*y*2.4,M=r+g*i*y*2.4,N=(p+1.4)/2.8;e.beginPath(),e.arc(O,M,.4+N*.8,0,Math.PI*2),e.fillStyle=`hsla(${t.hueShift+(d+1)/2*80},100%,80%,${.12+N*.4})`,e.fill()}e.globalCompositeOperation="source-over"}_renderBackdrop(e,t,s,r,i,o){const n=e.createRadialGradient(t,s,0,t,s,r*2.2);n.addColorStop(0,`hsla(${o},90%,50%,${.04+.12*i})`),n.addColorStop(1,"hsla(0,0%,0%,0)"),e.fillStyle=n,e.fillRect(0,0,this.w,this.h)}_compositeBloom(e,t,s,r,i){if(i!=="low"){if(e.globalCompositeOperation="lighter",this.filterOk){try{e.filter=`blur(${3+r*3}px)`,e.globalAlpha=.65,e.drawImage(this.glow,0,0,t,s),e.filter="none",e.globalAlpha=1}catch{e.filter="none",e.globalAlpha=1}if(i==="high")try{e.filter=`blur(${10+r*8}px)`,e.globalAlpha=.3,e.drawImage(this.glow,0,0,t,s),e.filter="none",e.globalAlpha=1}catch{e.filter="none",e.globalAlpha=1}}else{e.globalAlpha=.2;const o=2;e.drawImage(this.glow,-o,0,t,s),e.drawImage(this.glow,o,0,t,s),e.drawImage(this.glow,0,-o,t,s),e.drawImage(this.glow,0,o,t,s),e.globalAlpha=1}e.globalCompositeOperation="source-over"}}_compositeCrisp(e,t,s){e.globalCompositeOperation="lighter",e.drawImage(this.glow,0,0,t,s),e.globalCompositeOperation="source-over"}_renderCursorGlow(e,t,s,r,i){if(this._effectiveTier==="low")return;const o=t+this._smoothMx*r*.7,n=s-this._smoothMy*r*.7;if(Math.hypot(o-t,n-s)>r*1.2)return;const c=e.createRadialGradient(o,n,0,o,n,28);c.addColorStop(0,`hsla(${i},90%,80%,0.2)`),c.addColorStop(1,`hsla(${i},90%,60%,0)`),e.fillStyle=c,e.fillRect(o-28,n-28,56,56)}_toneClamp(e,t,s){e.fillStyle="rgba(2,6,14,0.05)",e.fillRect(0,0,t,s)}_measureFrame(e){const t=performance.now()-e;if(this._lastFrameMs=t,this._frameTimes.push(t),this._frameTimes.length>30&&this._frameTimes.shift(),this._frameTimes.length<10)return;const s=this._frameTimes.reduce((r,i)=>r+i,0)/this._frameTimes.length;if(s>12&&this._effectiveTier==="high")this._effectiveTier="medium";else if(s>12&&this._effectiveTier==="medium")this._effectiveTier="low";else if(s<6&&this._frameTimes.length>=30){const r=Re();this._effectiveTier==="low"&&r!=="low"?this._effectiveTier="medium":this._effectiveTier==="medium"&&r==="high"&&(this._effectiveTier="high")}}_renderDebug(e,t,s,r){e.fillStyle="rgba(0,0,0,0.75)",e.fillRect(8,8,210,100),e.font="11px monospace",e.fillStyle="#0f0",e.fillText(`frame: ${this._lastFrameMs.toFixed(1)}ms`,14,24),e.fillText(`tier: ${this._effectiveTier} (base: ${Re()})`,14,38),e.fillText(`ripples: ${this.ripples.length}`,14,52),e.fillText(`hot-spots: ${this._hotCount}`,14,66),e.fillText(`audio: B${t.toFixed(2)} M${s.toFixed(2)} H${r.toFixed(2)}`,14,80),e.fillText(`status: ${this.status} | activity: ${this.activity.toFixed(2)}`,14,94)}render(){return f`<canvas></canvas>`}};oe.styles=H`
    :host { display: block; width: 100%; height: 100%; pointer-events: auto; cursor: pointer; }
    canvas { width: 100%; height: 100%; display: block; }
  `;Pe([V({attribute:!1})],oe.prototype,"activity",2);Pe([V({attribute:!1})],oe.prototype,"status",2);Pe([V({attribute:!1})],oe.prototype,"micLevels",2);Pe([V({attribute:!1})],oe.prototype,"ttsLevels",2);oe=Pe([q("neural-sphere")],oe);var Gi=Object.defineProperty,Bi=Object.getOwnPropertyDescriptor,gt=(e,t,s,r)=>{for(var i=r>1?void 0:r?Bi(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Gi(t,s,i),i};const jt=["intelligence","system","personal","core"];let Ce=class extends E{constructor(){super(...arguments),this.selected="",this._hover=-1}_select(e){this.dispatchEvent(new CustomEvent("tool-select",{detail:e.id,bubbles:!0,composed:!0}))}_scale(e){if(this._hover<0)return 1;const t=Math.abs(e-this._hover);return t===0?1.5:t===1?1.28:t===2?1.12:1}_lift(e){if(this._hover<0)return 0;const t=Math.abs(e-this._hover);return t===0?-8:t===1?-4:t===2?-1:0}render(){const e=[...ls].sort((t,s)=>jt.indexOf(t.group)-jt.indexOf(s.group));return f`
      <div class="dock" @pointerleave=${()=>this._hover=-1}>
        ${e.map((t,s)=>{const r=e[s-1],i=r&&r.group!==t.group?f`<div class="sep"></div>`:null;return f`
            ${i}
            <button
              class="pill ${this.selected===t.id?"on":""}"
              style="--s:${this._scale(s)}; --ty:${this._lift(s)}px"
              @pointerenter=${()=>this._hover=s}
              @click=${()=>this._select(t)}
              aria-label=${t.label}
            >
              <span class="icon">${t.icon}</span>
              <span class="tip">${t.label}</span>
            </button>
          `})}
      </div>
    `}};Ce.styles=H`
    :host {
      display: block;
      pointer-events: none;
    }

    .dock {
      position: relative;
      isolation: isolate;
      pointer-events: auto;
      display: inline-flex;
      align-items: flex-end;
      gap: 6px;
      padding: 10px 14px;
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(16,20,40,0.5), rgba(10,12,26,0.66));
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid transparent;
      box-shadow:
        0 18px 50px rgba(0,0,0,0.5),
        0 0 50px rgba(140,160,255,0.10),
        inset 0 1px 0 rgba(255,255,255,0.08);
      max-width: 92vw;
      overflow: visible;
    }
    /* Animated iridescent gradient border */
    .dock::before {
      content: "";
      position: absolute; inset: 0;
      border-radius: inherit;
      padding: 1.4px;
      background: linear-gradient(120deg,
        #a8edea, #8fd3ff, #b8a6ff, #ff9ed8, #ffd6a5, #a8edea);
      background-size: 320% 320%;
      animation: irid-border 9s ease infinite;
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      pointer-events: none;
      z-index: -1;
      opacity: 0.8;
    }
    /* Holographic sheen sweep across the glass */
    .dock::after {
      content: "";
      position: absolute; inset: 0;
      border-radius: inherit;
      background: linear-gradient(115deg,
        transparent 30%, rgba(255,255,255,0.10) 48%, rgba(184,166,255,0.12) 54%, transparent 70%);
      background-size: 280% 100%;
      animation: irid-sheen 7s linear infinite;
      pointer-events: none;
      z-index: -1;
      mix-blend-mode: screen;
    }
    @keyframes irid-border {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    @keyframes irid-sheen {
      0% { background-position: 180% 0; }
      100% { background-position: -80% 0; }
    }

    .sep {
      width: 1px;
      align-self: center;
      height: 26px;
      margin: 0 4px;
      background: linear-gradient(180deg, transparent, rgba(184,166,255,0.4), transparent);
      flex: 0 0 auto;
    }

    .pill {
      position: relative;
      flex: 0 0 auto;
      width: 44px; height: 44px;
      border: 1px solid transparent;
      border-radius: 14px;
      background: rgba(255,255,255,0.04);
      color: rgba(210,235,255,0.82);
      cursor: pointer;
      display: grid; place-items: center;
      transform-origin: bottom center;
      transform: scale(var(--s, 1)) translateY(var(--ty, 0));
      transition:
        transform 0.18s cubic-bezier(0.22,1,0.36,1),
        background 0.16s ease,
        border-color 0.16s ease,
        box-shadow 0.16s ease;
    }
    .pill:hover { background: rgba(184,166,255,0.12); border-color: rgba(184,166,255,0.35); }
    .pill.on {
      background: rgba(143,211,255,0.16);
      border-color: rgba(184,166,255,0.55);
      box-shadow: 0 0 24px rgba(143,211,255,0.3), 0 0 36px rgba(255,158,216,0.16), inset 0 0 12px rgba(184,166,255,0.14);
    }
    .pill.on::after {
      content: "";
      position: absolute; bottom: -7px; left: 50%; transform: translateX(-50%);
      width: 14px; height: 4px; border-radius: 999px;
      background: linear-gradient(90deg, #8fd3ff, #b8a6ff, #ff9ed8);
      box-shadow: 0 0 10px rgba(184,166,255,0.8);
    }

    .icon {
      font-size: 1.15rem; line-height: 1;
      background: linear-gradient(135deg, #b6f0ff, #9fb8ff, #d9b3ff, #ffb3e6);
      background-size: 200% 200%;
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent; color: transparent;
      filter: drop-shadow(0 0 8px rgba(143,211,255,0.45));
      animation: irid-icon 9s ease infinite;
    }
    .pill.on .icon { filter: drop-shadow(0 0 12px rgba(184,166,255,0.9)); }
    @keyframes irid-icon {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }

    /* Hover label tooltip */
    .tip {
      position: absolute;
      bottom: calc(100% + 12px);
      left: 50%; transform: translateX(-50%) translateY(6px);
      padding: 5px 12px;
      border-radius: 9px;
      font-family: var(--ds-font-mono, monospace);
      font-size: 0.66rem; letter-spacing: 0.12em; text-transform: uppercase;
      white-space: nowrap;
      color: #eaffff;
      background: rgba(10,14,28,0.92);
      border: 1px solid rgba(184,166,255,0.35);
      box-shadow: 0 8px 24px rgba(0,0,0,0.5), 0 0 16px rgba(143,211,255,0.18);
      opacity: 0; pointer-events: none;
      transition: opacity 0.15s ease, transform 0.15s ease;
    }
    .pill:hover .tip { opacity: 1; transform: translateX(-50%) translateY(0); }
    .tip::after {
      content: "";
      position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
      border: 5px solid transparent; border-top-color: rgba(184,166,255,0.35);
    }

    @media (prefers-reduced-motion: reduce) {
      .pill { transition: background 0.16s ease, border-color 0.16s ease; transform: none !important; }
    }
  `;gt([V()],Ce.prototype,"selected",2);gt([x()],Ce.prototype,"_hover",2);Ce=gt([q("tool-dock")],Ce);var Yi=Object.defineProperty,Ki=Object.getOwnPropertyDescriptor,J=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ki(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Yi(t,s,i),i};let F=class extends Yt(E){constructor(){super(...arguments),this.activity=0,this.status="idle",this._openTool="",this._toolView=null,this._loadingTool=!1,this._draft="",this._micLevels=null,this._audioAnalyser=null,this._audioRaf=0,this._onSphereListen=()=>{this._startMic()},this._onSphereCommand=()=>{var t;const e=document.querySelector("command-palette");(t=e==null?void 0:e.toggle)==null||t.call(e)},this._onKey=e=>{e.key==="Escape"&&this._openTool&&this._closeTool()}}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._stopAudio()}async _startMic(){var s;if((s=this._audioAnalyser)!=null&&s.connected)return;if(this._audioAnalyser=new Ui,!await this._audioAnalyser.connectMic()){this._audioAnalyser=null;return}const t=()=>{this._audioAnalyser&&(this._audioAnalyser.update(),this._micLevels={...this._audioAnalyser.levels},this._audioRaf=requestAnimationFrame(t))};this._audioRaf=requestAnimationFrame(t)}_stopAudio(){var e;cancelAnimationFrame(this._audioRaf),(e=this._audioAnalyser)==null||e.destroy(),this._audioAnalyser=null,this._micLevels=null}async _selectTool(e){const t=zt(e);if(t){this._openTool=e,this.setAttribute("data-focus",""),this._loadingTool=!0,this._toolView=null;try{await t.load(),this._toolView=t.render()}catch{this._toolView=f`<div class="focus-loading">Failed to load ${t.label}.</div>`}this._loadingTool=!1}}_closeTool(){this._openTool="",this._toolView=null,this.removeAttribute("data-focus")}_send(){const e=this._draft.trim();e&&(mi(e),this._draft="")}render(){const e=P.get().slice(-6),t=this._openTool?zt(this._openTool):null;return f`
      <div class="stage">
        <neural-sphere
          .activity=${this.activity}
          .status=${this.status}
          .micLevels=${this._micLevels}
          @sphere-listen=${this._onSphereListen}
          @sphere-command=${this._onSphereCommand}
        ></neural-sphere>

        ${t?f`
          <div class="focus">
            <div class="focus-head">
              <span>${t.icon}</span><span>${t.label}</span>
              <span class="spacer"></span>
              <button class="focus-close" @click=${this._closeTool}>✕ Close (Esc)</button>
            </div>
            <div class="focus-body">
              ${this._loadingTool?f`<div class="focus-loading">Loading ${t.label}…</div>`:this._toolView}
            </div>
          </div>
        `:null}

        <div class="dock">
          ${e.length?f`
            <div class="transcript">
              ${e.map(s=>f`<div class="msg ${s.role}">${s.text}</div>`)}
            </div>`:null}
          ${L.get()?f`<div class="thinking">DEEP is thinking…</div>`:null}
          <div class="composer">
            <input
              .value=${this._draft}
              placeholder="Talk to DEEP…"
              @input=${s=>this._draft=s.target.value}
              @keydown=${s=>{s.key==="Enter"&&!s.shiftKey&&(s.preventDefault(),this._send())}}
            />
            <button class="send" title="Send" @click=${this._send}>➤</button>
          </div>
        </div>
      </div>

      <tool-dock .selected=${this._openTool} @tool-select=${s=>this._selectTool(s.detail)}></tool-dock>
    `}};F.styles=H`
    :host {
      position: absolute; inset: 0; z-index: 20;
      pointer-events: none;
      font-family: var(--ds-font-sans, system-ui);
      color: rgba(220,240,255,0.92);
    }

    .stage { position: absolute; inset: 0; overflow: hidden; }
    /* Holographic aurora ambient — soft, slow-drifting iridescent glows */
    .stage::before {
      content: "";
      position: absolute; inset: -12%;
      z-index: 0; pointer-events: none;
      background:
        radial-gradient(38% 48% at 30% 34%, rgba(143,211,255,0.12), transparent 70%),
        radial-gradient(44% 54% at 72% 60%, rgba(184,166,255,0.12), transparent 70%),
        radial-gradient(40% 46% at 54% 80%, rgba(255,158,216,0.09), transparent 70%),
        radial-gradient(36% 42% at 80% 22%, rgba(168,237,234,0.08), transparent 70%);
      filter: blur(44px) saturate(140%);
      animation: aurora-drift 26s ease-in-out infinite alternate;
    }
    @keyframes aurora-drift {
      0%   { transform: translate3d(-2%, -1%, 0) scale(1);    opacity: 0.85; }
      50%  { transform: translate3d(2%, 1.5%, 0) scale(1.06); opacity: 1; }
      100% { transform: translate3d(-1%, 2%, 0) scale(1.02);  opacity: 0.9; }
    }
    @media (prefers-reduced-motion: reduce) { .stage::before { animation: none; } }
    neural-sphere { position: absolute; inset: 0; z-index: 1; transition: opacity 0.5s ease, filter 0.5s ease; }
    :host([data-focus]) neural-sphere { opacity: 0.18; filter: blur(3px); }

    /* Glassmorphic tool dock — floating, bottom-centered */
    tool-dock {
      position: absolute;
      left: 0; right: 0; bottom: 22px;
      display: flex; justify-content: center;
      z-index: 8; pointer-events: none;
    }

    /* Focus surface — full tool view over the stage */
    .focus {
      position: absolute; top: 24px; left: 24px; bottom: 24px; right: 24px; z-index: 5;
      pointer-events: auto;
      background: rgba(6,11,20,0.82);
      backdrop-filter: blur(20px) saturate(140%);
      -webkit-backdrop-filter: blur(20px) saturate(140%);
      border: 1px solid rgba(0,229,255,0.22);
      border-radius: 16px;
      box-shadow: 0 24px 80px rgba(0,0,0,0.6), 0 0 60px rgba(0,229,255,0.08);
      display: flex; flex-direction: column; overflow: hidden;
      animation: focus-in 0.32s cubic-bezier(0.16,1,0.3,1);
    }
    @keyframes focus-in { from { opacity: 0; transform: translateY(14px) scale(0.985); } to { opacity: 1; transform: none; } }
    .focus-head {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 18px; border-bottom: 1px solid rgba(0,229,255,0.14);
      font-family: var(--ds-font-mono, monospace);
      letter-spacing: 0.14em; text-transform: uppercase; font-size: 0.78rem;
      color: rgba(0,229,255,0.9);
    }
    .focus-head .spacer { flex: 1; }
    .focus-close {
      pointer-events: auto; cursor: pointer; font: inherit; font-size: 0.7rem;
      color: rgba(220,240,255,0.8); background: rgba(0,229,255,0.08);
      border: 1px solid rgba(0,229,255,0.25); border-radius: 8px; padding: 5px 12px;
      transition: all 0.15s ease;
    }
    .focus-close:hover { background: rgba(255,80,80,0.12); border-color: rgba(255,80,80,0.5); color: #fff; }
    .focus-body { flex: 1; overflow: auto; }
    .focus-loading { display: grid; place-items: center; height: 100%; color: rgba(0,229,255,0.6); letter-spacing: 0.2em; }

    /* Chat dock — centered, stacked above the tool dock */
    .dock {
      position: absolute;
      left: 0; right: 0; bottom: 104px;
      max-width: 680px; margin: 0 auto;
      padding: 0 20px;
      z-index: 6; pointer-events: none;
    }
    .transcript {
      pointer-events: auto;
      max-height: 34vh; overflow-y: auto; margin-bottom: 10px;
      display: flex; flex-direction: column; gap: 8px;
      mask-image: linear-gradient(to top, black 80%, transparent);
    }
    .msg { font-size: 0.9rem; line-height: 1.45; padding: 8px 14px; border-radius: 12px; max-width: 88%; white-space: pre-wrap; }
    .msg.user { align-self: flex-end; background: rgba(143,211,255,0.12); border: 1px solid rgba(143,211,255,0.28); }
    .msg.ai { align-self: flex-start; background: rgba(184,166,255,0.08); border: 1px solid rgba(184,166,255,0.18); }
    .composer {
      position: relative; isolation: isolate;
      pointer-events: auto;
      display: flex; align-items: center; gap: 10px;
      background: rgba(8,12,24,0.82);
      backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px) saturate(180%);
      border: 1px solid transparent; border-radius: 999px;
      padding: 6px 6px 6px 18px;
      box-shadow: 0 0 44px rgba(140,160,255,0.14), 0 8px 30px rgba(0,0,0,0.5);
    }
    /* Animated iridescent gradient border on the composer */
    .composer::before {
      content: ""; position: absolute; inset: 0; border-radius: inherit;
      padding: 1.4px;
      background: linear-gradient(120deg, #a8edea, #8fd3ff, #b8a6ff, #ff9ed8, #ffd6a5, #a8edea);
      background-size: 320% 320%;
      animation: irid-border 9s ease infinite;
      -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
      -webkit-mask-composite: xor; mask-composite: exclude;
      pointer-events: none; z-index: -1; opacity: 0.8;
    }
    @keyframes irid-border {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    .composer input {
      flex: 1; background: none; border: none; outline: none;
      color: #eaffff; font: inherit; font-size: 0.95rem;
    }
    .composer input::placeholder { color: rgba(190,205,255,0.42); }
    .send {
      cursor: pointer; border: none; border-radius: 999px; width: 38px; height: 38px;
      background: linear-gradient(135deg, #8fd3ff, #b8a6ff, #ff9ed8); color: #0a0e1c;
      background-size: 200% 200%; animation: irid-icon 8s ease infinite;
      font-size: 1.1rem; display: grid; place-items: center;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .send:hover { transform: scale(1.08); box-shadow: 0 0 22px rgba(184,166,255,0.6); }
    @keyframes irid-icon {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    .thinking {
      font-size: 0.72rem; letter-spacing: 0.15em; margin: 0 0 6px 16px;
      background: linear-gradient(90deg, #8fd3ff, #b8a6ff, #ff9ed8);
      background-size: 200% 200%;
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent; color: transparent;
      animation: irid-icon 6s ease infinite;
    }
  `;J([V({attribute:!1})],F.prototype,"activity",2);J([V({attribute:!1})],F.prototype,"status",2);J([x()],F.prototype,"_openTool",2);J([x()],F.prototype,"_toolView",2);J([x()],F.prototype,"_loadingTool",2);J([x()],F.prototype,"_draft",2);J([x()],F.prototype,"_micLevels",2);F=J([q("deep-console")],F);var Xi=Object.defineProperty,Ji=Object.getOwnPropertyDescriptor,ds=(e,t,s,r)=>{for(var i=r>1?void 0:r?Ji(t,s):t,o=e.length-1,n;o>=0;o--)(n=e[o])&&(i=(r?n(t,s,i):n(i))||i);return r&&i&&Xi(t,s,i),i};let qe=class extends Yt(E){constructor(){super(...arguments),this._hudActive=!0,this.onGlobalKey=e=>{var t;(e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"&&(e.preventDefault(),(t=this.renderRoot.querySelector("command-palette"))==null||t.toggle()),(e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key.toLowerCase()==="h"&&(e.preventDefault(),this._hudActive=!this._hudActive)},this.activity=new Map,this.statusTimer=0,this.onTelemetry=e=>{const t=e.type??"";t.startsWith("agent_")?this.bumpNode("agents","active"):t==="security_alert"?this.bumpNode("security","warning",6e3):t.includes("proximity")||t.includes("device")||t.includes("unknown_ap")?this.bumpNode("security","indexing"):t.startsWith("predictive_")||t.startsWith("proactive_")?this.bumpNode("predictive","thinking"):t.startsWith("knowledge_")||t.startsWith("entity_")?this.bumpNode("memory","indexing"):t.startsWith("network_")||t==="device_joined"?this.bumpNode("network","active"):t.startsWith("research_")&&this.bumpNode("research","active")}}bumpNode(e,t,s=3500){this.activity.set(e,{status:t,until:Date.now()+s}),this.requestUpdate()}connectedCallback(){super.connectedCallback(),bi(),ze.on(this.onTelemetry),this.pollStatus(),this.statusTimer=window.setInterval(()=>this.pollStatus(),15e3),window.addEventListener("keydown",this.onGlobalKey)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.statusTimer),window.removeEventListener("keydown",this.onGlobalKey)}async pollStatus(){try{const t=await(await fetch("/api/status")).json();this.bumpNode("system",(t==null?void 0:t.brain)==="ok"?"idle":"warning",16e3)}catch{this.bumpNode("system","warning",16e3)}}brainState(){const e=Date.now(),t={};for(const[r,i]of this.activity)i.until>e&&(t[r]=i.status);const s=this.getOrbState();return at.get()?t.chat="speaking":L.get()&&(t.chat="active"),L.get()&&(t.reasoning="thinking"),s==="listening"?t.voice="active":s==="speaking"&&(t.voice="speaking"),We.get()!=="open"&&(t.system="warning"),t}fieldState(e){const t=["warning","speaking","thinking","indexing","active"];let s=0,r="idle";const i=new Set(Object.values(e));for(const o of t)if(i.has(o)){r=o;break}for(const o of Object.values(e))o&&o!=="idle"&&s++;return{activity:Math.min(1,s/4),status:r}}getOrbState(){return at.get()?"speaking":L.get()?"thinking":"idle"}render(){const e=this.fieldState(this.brainState());return f`
      <!-- Cinematic background layer (disabled for now) -->

      <!-- Boot splash -->
      <deep-boot></deep-boot>

      <!-- Toast notifications -->
      <toast-stack></toast-stack>

      <!-- Command palette (Cmd+K) -->
      <command-palette></command-palette>

      <!-- Voice status indicator -->
      <voice-status-orb></voice-status-orb>

      <!-- THE CONSOLE — neural sphere + elements panel + chat dock. The primary
           interface; tools are added steadily via TOOL_REGISTRY. -->
      <deep-console .activity=${e.activity} .status=${e.status}></deep-console>
    `}};qe.styles=H`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      background: #06080c;
    }
  `;ds([x()],qe.prototype,"_hudActive",2);qe=ds([q("deep-app")],qe);export{Tr as A,Rt as B,wr as C,_r as D,xr as E,$ as F,Zi as G,rr as H,or as I,nr as J,ar as K,cr as L,pe as M,Zs as N,lr as O,hr as P,pr as Q,ur as R,dr as S,fr as T,mr as U,vr as V,br as W,gr as X,yr as Y,sr as a,ir as b,tr as c,f as d,H as e,er as f,te as g,di as h,E as i,Ir as j,Rr as k,Dr as l,Yt as m,V as n,$r as o,Sr as p,kr as q,x as r,Cr as s,q as t,Or as u,Mr as v,Nr as w,Ar as x,Er as y,Pr as z};
//# sourceMappingURL=index-BZpHEIVQ.js.map
