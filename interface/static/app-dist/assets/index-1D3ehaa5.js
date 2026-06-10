var $i=Object.defineProperty;var Ti=(t,e,r)=>e in t?$i(t,e,{enumerable:!0,configurable:!0,writable:!0,value:r}):t[e]=r;var O=(t,e,r)=>Ti(t,typeof e!="symbol"?e+"":e,r);(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))n(s);new MutationObserver(s=>{for(const i of s)if(i.type==="childList")for(const o of i.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&n(o)}).observe(document,{childList:!0,subtree:!0});function r(s){const i={};return s.integrity&&(i.integrity=s.integrity),s.referrerPolicy&&(i.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?i.credentials="include":s.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function n(s){if(s.ep)return;s.ep=!0;const i=r(s);fetch(s.href,i)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Zt=globalThis,ss=Zt.ShadowRoot&&(Zt.ShadyCSS===void 0||Zt.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ns=Symbol(),Vs=new WeakMap;let Dn=class{constructor(e,r,n){if(this._$cssResult$=!0,n!==ns)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=r}get styleSheet(){let e=this.o;const r=this.t;if(ss&&e===void 0){const n=r!==void 0&&r.length===1;n&&(e=Vs.get(r)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),n&&Vs.set(r,e))}return e}toString(){return this.cssText}};const Si=t=>new Dn(typeof t=="string"?t:t+"",void 0,ns),ae=(t,...e)=>{const r=t.length===1?t[0]:e.reduce((n,s,i)=>n+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new Dn(r,t,ns)},Ai=(t,e)=>{if(ss)t.adoptedStyleSheets=e.map(r=>r instanceof CSSStyleSheet?r:r.styleSheet);else for(const r of e){const n=document.createElement("style"),s=Zt.litNonce;s!==void 0&&n.setAttribute("nonce",s),n.textContent=r.cssText,t.appendChild(n)}},Zs=ss?t=>t:t=>t instanceof CSSStyleSheet?(e=>{let r="";for(const n of e.cssRules)r+=n.cssText;return Si(r)})(t):t;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:Ei,defineProperty:Ri,getOwnPropertyDescriptor:Ci,getOwnPropertyNames:Oi,getOwnPropertySymbols:Pi,getPrototypeOf:Di}=Object,Se=globalThis,Ks=Se.trustedTypes,Ni=Ks?Ks.emptyScript:"",Or=Se.reactiveElementPolyfillSupport,wt=(t,e)=>t,Xt={toAttribute(t,e){switch(e){case Boolean:t=t?Ni:null;break;case Object:case Array:t=t==null?t:JSON.stringify(t)}return t},fromAttribute(t,e){let r=t;switch(e){case Boolean:r=t!==null;break;case Number:r=t===null?null:Number(t);break;case Object:case Array:try{r=JSON.parse(t)}catch{r=null}}return r}},is=(t,e)=>!Ei(t,e),Xs={attribute:!0,type:String,converter:Xt,reflect:!1,useDefault:!1,hasChanged:is};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),Se.litPropertyMetadata??(Se.litPropertyMetadata=new WeakMap);let Ke=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??(this.l=[])).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,r=Xs){if(r.state&&(r.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((r=Object.create(r)).wrapped=!0),this.elementProperties.set(e,r),!r.noAccessor){const n=Symbol(),s=this.getPropertyDescriptor(e,n,r);s!==void 0&&Ri(this.prototype,e,s)}}static getPropertyDescriptor(e,r,n){const{get:s,set:i}=Ci(this.prototype,e)??{get(){return this[r]},set(o){this[r]=o}};return{get:s,set(o){const c=s==null?void 0:s.call(this);i==null||i.call(this,o),this.requestUpdate(e,c,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??Xs}static _$Ei(){if(this.hasOwnProperty(wt("elementProperties")))return;const e=Di(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(wt("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(wt("properties"))){const r=this.properties,n=[...Oi(r),...Pi(r)];for(const s of n)this.createProperty(s,r[s])}const e=this[Symbol.metadata];if(e!==null){const r=litPropertyMetadata.get(e);if(r!==void 0)for(const[n,s]of r)this.elementProperties.set(n,s)}this._$Eh=new Map;for(const[r,n]of this.elementProperties){const s=this._$Eu(r,n);s!==void 0&&this._$Eh.set(s,r)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const r=[];if(Array.isArray(e)){const n=new Set(e.flat(1/0).reverse());for(const s of n)r.unshift(Zs(s))}else e!==void 0&&r.push(Zs(e));return r}static _$Eu(e,r){const n=r.attribute;return n===!1?void 0:typeof n=="string"?n:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(r=>this.enableUpdating=r),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(r=>r(this))}addController(e){var r;(this._$EO??(this._$EO=new Set)).add(e),this.renderRoot!==void 0&&this.isConnected&&((r=e.hostConnected)==null||r.call(e))}removeController(e){var r;(r=this._$EO)==null||r.delete(e)}_$E_(){const e=new Map,r=this.constructor.elementProperties;for(const n of r.keys())this.hasOwnProperty(n)&&(e.set(n,this[n]),delete this[n]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Ai(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(r=>{var n;return(n=r.hostConnected)==null?void 0:n.call(r)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(r=>{var n;return(n=r.hostDisconnected)==null?void 0:n.call(r)})}attributeChangedCallback(e,r,n){this._$AK(e,n)}_$ET(e,r){var i;const n=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,n);if(s!==void 0&&n.reflect===!0){const o=(((i=n.converter)==null?void 0:i.toAttribute)!==void 0?n.converter:Xt).toAttribute(r,n.type);this._$Em=e,o==null?this.removeAttribute(s):this.setAttribute(s,o),this._$Em=null}}_$AK(e,r){var i,o;const n=this.constructor,s=n._$Eh.get(e);if(s!==void 0&&this._$Em!==s){const c=n.getPropertyOptions(s),l=typeof c.converter=="function"?{fromAttribute:c.converter}:((i=c.converter)==null?void 0:i.fromAttribute)!==void 0?c.converter:Xt;this._$Em=s;const p=l.fromAttribute(r,c.type);this[s]=p??((o=this._$Ej)==null?void 0:o.get(s))??p,this._$Em=null}}requestUpdate(e,r,n,s=!1,i){var o;if(e!==void 0){const c=this.constructor;if(s===!1&&(i=this[e]),n??(n=c.getPropertyOptions(e)),!((n.hasChanged??is)(i,r)||n.useDefault&&n.reflect&&i===((o=this._$Ej)==null?void 0:o.get(e))&&!this.hasAttribute(c._$Eu(e,n))))return;this.C(e,r,n)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,r,{useDefault:n,reflect:s,wrapped:i},o){n&&!(this._$Ej??(this._$Ej=new Map)).has(e)&&(this._$Ej.set(e,o??r??this[e]),i!==!0||o!==void 0)||(this._$AL.has(e)||(this.hasUpdated||n||(r=void 0),this._$AL.set(e,r)),s===!0&&this._$Em!==e&&(this._$Eq??(this._$Eq=new Set)).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(r){Promise.reject(r)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var n;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[i,o]of this._$Ep)this[i]=o;this._$Ep=void 0}const s=this.constructor.elementProperties;if(s.size>0)for(const[i,o]of s){const{wrapped:c}=o,l=this[i];c!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,o,l)}}let e=!1;const r=this._$AL;try{e=this.shouldUpdate(r),e?(this.willUpdate(r),(n=this._$EO)==null||n.forEach(s=>{var i;return(i=s.hostUpdate)==null?void 0:i.call(s)}),this.update(r)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(r)}willUpdate(e){}_$AE(e){var r;(r=this._$EO)==null||r.forEach(n=>{var s;return(s=n.hostUpdated)==null?void 0:s.call(n)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(r=>this._$ET(r,this[r]))),this._$EM()}updated(e){}firstUpdated(e){}};Ke.elementStyles=[],Ke.shadowRootOptions={mode:"open"},Ke[wt("elementProperties")]=new Map,Ke[wt("finalized")]=new Map,Or==null||Or({ReactiveElement:Ke}),(Se.reactiveElementVersions??(Se.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const xt=globalThis,Qs=t=>t,Qt=xt.trustedTypes,Js=Qt?Qt.createPolicy("lit-html",{createHTML:t=>t}):void 0,Nn="$lit$",$e=`lit$${Math.random().toFixed(9).slice(2)}$`,In="?"+$e,Ii=`<${In}>`,Ie=document,_t=()=>Ie.createComment(""),$t=t=>t===null||typeof t!="object"&&typeof t!="function",as=Array.isArray,Li=t=>as(t)||typeof(t==null?void 0:t[Symbol.iterator])=="function",Pr=`[ 	
\f\r]`,gt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,en=/-->/g,tn=/>/g,Ce=RegExp(`>|${Pr}(?:([^\\s"'>=/]+)(${Pr}*=${Pr}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),rn=/'/g,sn=/"/g,Ln=/^(?:script|style|textarea|title)$/i,Mi=t=>(e,...r)=>({_$litType$:t,strings:e,values:r}),_=Mi(1),Le=Symbol.for("lit-noChange"),H=Symbol.for("lit-nothing"),nn=new WeakMap,De=Ie.createTreeWalker(Ie,129);function Mn(t,e){if(!as(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return Js!==void 0?Js.createHTML(e):e}const zi=(t,e)=>{const r=t.length-1,n=[];let s,i=e===2?"<svg>":e===3?"<math>":"",o=gt;for(let c=0;c<r;c++){const l=t[c];let p,d,h=-1,m=0;for(;m<l.length&&(o.lastIndex=m,d=o.exec(l),d!==null);)m=o.lastIndex,o===gt?d[1]==="!--"?o=en:d[1]!==void 0?o=tn:d[2]!==void 0?(Ln.test(d[2])&&(s=RegExp("</"+d[2],"g")),o=Ce):d[3]!==void 0&&(o=Ce):o===Ce?d[0]===">"?(o=s??gt,h=-1):d[1]===void 0?h=-2:(h=o.lastIndex-d[2].length,p=d[1],o=d[3]===void 0?Ce:d[3]==='"'?sn:rn):o===sn||o===rn?o=Ce:o===en||o===tn?o=gt:(o=Ce,s=void 0);const R=o===Ce&&t[c+1].startsWith("/>")?" ":"";i+=o===gt?l+Ii:h>=0?(n.push(p),l.slice(0,h)+Nn+l.slice(h)+$e+R):l+$e+(h===-2?c:R)}return[Mn(t,i+(t[r]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),n]};class Tt{constructor({strings:e,_$litType$:r},n){let s;this.parts=[];let i=0,o=0;const c=e.length-1,l=this.parts,[p,d]=zi(e,r);if(this.el=Tt.createElement(p,n),De.currentNode=this.el.content,r===2||r===3){const h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(s=De.nextNode())!==null&&l.length<c;){if(s.nodeType===1){if(s.hasAttributes())for(const h of s.getAttributeNames())if(h.endsWith(Nn)){const m=d[o++],R=s.getAttribute(h).split($e),g=/([.?@])?(.*)/.exec(m);l.push({type:1,index:i,name:g[2],strings:R,ctor:g[1]==="."?Hi:g[1]==="?"?Fi:g[1]==="@"?Bi:or}),s.removeAttribute(h)}else h.startsWith($e)&&(l.push({type:6,index:i}),s.removeAttribute(h));if(Ln.test(s.tagName)){const h=s.textContent.split($e),m=h.length-1;if(m>0){s.textContent=Qt?Qt.emptyScript:"";for(let R=0;R<m;R++)s.append(h[R],_t()),De.nextNode(),l.push({type:2,index:++i});s.append(h[m],_t())}}}else if(s.nodeType===8)if(s.data===In)l.push({type:2,index:i});else{let h=-1;for(;(h=s.data.indexOf($e,h+1))!==-1;)l.push({type:7,index:i}),h+=$e.length-1}i++}}static createElement(e,r){const n=Ie.createElement("template");return n.innerHTML=e,n}}function Je(t,e,r=t,n){var o,c;if(e===Le)return e;let s=n!==void 0?(o=r._$Co)==null?void 0:o[n]:r._$Cl;const i=$t(e)?void 0:e._$litDirective$;return(s==null?void 0:s.constructor)!==i&&((c=s==null?void 0:s._$AO)==null||c.call(s,!1),i===void 0?s=void 0:(s=new i(t),s._$AT(t,r,n)),n!==void 0?(r._$Co??(r._$Co=[]))[n]=s:r._$Cl=s),s!==void 0&&(e=Je(t,s._$AS(t,e.values),s,n)),e}class Ui{constructor(e,r){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=r}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:r},parts:n}=this._$AD,s=((e==null?void 0:e.creationScope)??Ie).importNode(r,!0);De.currentNode=s;let i=De.nextNode(),o=0,c=0,l=n[0];for(;l!==void 0;){if(o===l.index){let p;l.type===2?p=new Rt(i,i.nextSibling,this,e):l.type===1?p=new l.ctor(i,l.name,l.strings,this,e):l.type===6&&(p=new ji(i,this,e)),this._$AV.push(p),l=n[++c]}o!==(l==null?void 0:l.index)&&(i=De.nextNode(),o++)}return De.currentNode=Ie,s}p(e){let r=0;for(const n of this._$AV)n!==void 0&&(n.strings!==void 0?(n._$AI(e,n,r),r+=n.strings.length-2):n._$AI(e[r])),r++}}class Rt{get _$AU(){var e;return((e=this._$AM)==null?void 0:e._$AU)??this._$Cv}constructor(e,r,n,s){this.type=2,this._$AH=H,this._$AN=void 0,this._$AA=e,this._$AB=r,this._$AM=n,this.options=s,this._$Cv=(s==null?void 0:s.isConnected)??!0}get parentNode(){let e=this._$AA.parentNode;const r=this._$AM;return r!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=r.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,r=this){e=Je(this,e,r),$t(e)?e===H||e==null||e===""?(this._$AH!==H&&this._$AR(),this._$AH=H):e!==this._$AH&&e!==Le&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Li(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==H&&$t(this._$AH)?this._$AA.nextSibling.data=e:this.T(Ie.createTextNode(e)),this._$AH=e}$(e){var i;const{values:r,_$litType$:n}=e,s=typeof n=="number"?this._$AC(e):(n.el===void 0&&(n.el=Tt.createElement(Mn(n.h,n.h[0]),this.options)),n);if(((i=this._$AH)==null?void 0:i._$AD)===s)this._$AH.p(r);else{const o=new Ui(s,this),c=o.u(this.options);o.p(r),this.T(c),this._$AH=o}}_$AC(e){let r=nn.get(e.strings);return r===void 0&&nn.set(e.strings,r=new Tt(e)),r}k(e){as(this._$AH)||(this._$AH=[],this._$AR());const r=this._$AH;let n,s=0;for(const i of e)s===r.length?r.push(n=new Rt(this.O(_t()),this.O(_t()),this,this.options)):n=r[s],n._$AI(i),s++;s<r.length&&(this._$AR(n&&n._$AB.nextSibling,s),r.length=s)}_$AR(e=this._$AA.nextSibling,r){var n;for((n=this._$AP)==null?void 0:n.call(this,!1,!0,r);e!==this._$AB;){const s=Qs(e).nextSibling;Qs(e).remove(),e=s}}setConnected(e){var r;this._$AM===void 0&&(this._$Cv=e,(r=this._$AP)==null||r.call(this,e))}}let or=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,r,n,s,i){this.type=1,this._$AH=H,this._$AN=void 0,this.element=e,this.name=r,this._$AM=s,this.options=i,n.length>2||n[0]!==""||n[1]!==""?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=H}_$AI(e,r=this,n,s){const i=this.strings;let o=!1;if(i===void 0)e=Je(this,e,r,0),o=!$t(e)||e!==this._$AH&&e!==Le,o&&(this._$AH=e);else{const c=e;let l,p;for(e=i[0],l=0;l<i.length-1;l++)p=Je(this,c[n+l],r,l),p===Le&&(p=this._$AH[l]),o||(o=!$t(p)||p!==this._$AH[l]),p===H?e=H:e!==H&&(e+=(p??"")+i[l+1]),this._$AH[l]=p}o&&!s&&this.j(e)}j(e){e===H?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},Hi=class extends or{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===H?void 0:e}},Fi=class extends or{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==H)}},Bi=class extends or{constructor(e,r,n,s,i){super(e,r,n,s,i),this.type=5}_$AI(e,r=this){if((e=Je(this,e,r,0)??H)===Le)return;const n=this._$AH,s=e===H&&n!==H||e.capture!==n.capture||e.once!==n.once||e.passive!==n.passive,i=e!==H&&(n===H||s);s&&this.element.removeEventListener(this.name,this,n),i&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var r;typeof this._$AH=="function"?this._$AH.call(((r=this.options)==null?void 0:r.host)??this.element,e):this._$AH.handleEvent(e)}},ji=class{constructor(e,r,n){this.element=e,this.type=6,this._$AN=void 0,this._$AM=r,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(e){Je(this,e)}};const Dr=xt.litHtmlPolyfillSupport;Dr==null||Dr(Tt,Rt),(xt.litHtmlVersions??(xt.litHtmlVersions=[])).push("3.3.3");const Wi=(t,e,r)=>{const n=(r==null?void 0:r.renderBefore)??e;let s=n._$litPart$;if(s===void 0){const i=(r==null?void 0:r.renderBefore)??null;n._$litPart$=s=new Rt(e.insertBefore(_t(),i),i,void 0,r??{})}return s._$AI(t),s};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ne=globalThis;let X=class extends Ke{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var r;const e=super.createRenderRoot();return(r=this.renderOptions).renderBefore??(r.renderBefore=e.firstChild),e}update(e){const r=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Wi(r,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return Le}};var Pn;X._$litElement$=!0,X.finalized=!0,(Pn=Ne.litElementHydrateSupport)==null||Pn.call(Ne,{LitElement:X});const Nr=Ne.litElementPolyfillSupport;Nr==null||Nr({LitElement:X});(Ne.litElementVersions??(Ne.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const oe=t=>(e,r)=>{r!==void 0?r.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const qi={attribute:!0,type:String,converter:Xt,reflect:!1,hasChanged:is},Gi=(t=qi,e,r)=>{const{kind:n,metadata:s}=r;let i=globalThis.litPropertyMetadata.get(s);if(i===void 0&&globalThis.litPropertyMetadata.set(s,i=new Map),n==="setter"&&((t=Object.create(t)).wrapped=!0),i.set(r.name,t),n==="accessor"){const{name:o}=r;return{set(c){const l=e.get.call(this);e.set.call(this,c),this.requestUpdate(o,l,t,!0,c)},init(c){return c!==void 0&&this.C(o,void 0,t,c),c}}}if(n==="setter"){const{name:o}=r;return function(c){const l=this[o];e.call(this,c),this.requestUpdate(o,l,t,!0,c)}}throw Error("Unsupported decorator location: "+n)};function le(t){return(e,r)=>typeof r=="object"?Gi(t,e,r):((n,s,i)=>{const o=s.hasOwnProperty(i);return s.constructor.createProperty(i,n),o?Object.getOwnPropertyDescriptor(s,i):void 0})(t,e,r)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function re(t){return le({...t,state:!0,attribute:!1})}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Yi=(t,e,r)=>(r.configurable=!0,r.enumerable=!0,Reflect.decorate&&typeof e!="object"&&Object.defineProperty(t,e,r),r);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function os(t,e){return(r,n,s)=>{const i=o=>{var c;return((c=o.renderRoot)==null?void 0:c.querySelector(t))??null};return Yi(r,n,{get(){return i(this)}})}}var Vi=Object.defineProperty,Zi=(t,e,r)=>e in t?Vi(t,e,{enumerable:!0,configurable:!0,writable:!0,value:r}):t[e]=r,Ir=(t,e,r)=>(Zi(t,typeof e!="symbol"?e+"":e,r),r),Ki=(t,e,r)=>{if(!e.has(t))throw TypeError("Cannot "+r)},Lr=(t,e)=>{if(Object(e)!==e)throw TypeError('Cannot use the "in" operator on this value');return t.has(e)},Wt=(t,e,r)=>{if(e.has(t))throw TypeError("Cannot add the same private member more than once");e instanceof WeakSet?e.add(t):e.set(t,r)},an=(t,e,r)=>(Ki(t,e,"access private method"),r);/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function zn(t,e){return Object.is(t,e)}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */let U=null,kt=!1,Kt=1;const Jt=Symbol("SIGNAL");function Qe(t){const e=U;return U=t,e}function Xi(){return U}function Qi(){return kt}const ls={version:0,lastCleanEpoch:0,dirty:!1,producerNode:void 0,producerLastReadVersion:void 0,producerIndexOfThis:void 0,nextProducerIndex:0,liveConsumerNode:void 0,liveConsumerIndexOfThis:void 0,consumerAllowSignalWrites:!1,consumerIsAlwaysLive:!1,producerMustRecompute:()=>!1,producerRecomputeValue:()=>{},consumerMarkedDirty:()=>{},consumerOnSignalRead:()=>{}};function lr(t){if(kt)throw new Error(typeof ngDevMode<"u"&&ngDevMode?"Assertion error: signal read during notification phase":"");if(U===null)return;U.consumerOnSignalRead(t);const e=U.nextProducerIndex++;if(et(U),e<U.producerNode.length&&U.producerNode[e]!==t&&Wr(U)){const r=U.producerNode[e];cr(r,U.producerIndexOfThis[e])}U.producerNode[e]!==t&&(U.producerNode[e]=t,U.producerIndexOfThis[e]=Wr(U)?Fn(t,U,e):0),U.producerLastReadVersion[e]=t.version}function Ji(){Kt++}function Un(t){if(!(!t.dirty&&t.lastCleanEpoch===Kt)){if(!t.producerMustRecompute(t)&&!na(t)){t.dirty=!1,t.lastCleanEpoch=Kt;return}t.producerRecomputeValue(t),t.dirty=!1,t.lastCleanEpoch=Kt}}function Hn(t){if(t.liveConsumerNode===void 0)return;const e=kt;kt=!0;try{for(const r of t.liveConsumerNode)r.dirty||ta(r)}finally{kt=e}}function ea(){return(U==null?void 0:U.consumerAllowSignalWrites)!==!1}function ta(t){var e;t.dirty=!0,Hn(t),(e=t.consumerMarkedDirty)==null||e.call(t.wrapper??t)}function ra(t){return t&&(t.nextProducerIndex=0),Qe(t)}function sa(t,e){if(Qe(e),!(!t||t.producerNode===void 0||t.producerIndexOfThis===void 0||t.producerLastReadVersion===void 0)){if(Wr(t))for(let r=t.nextProducerIndex;r<t.producerNode.length;r++)cr(t.producerNode[r],t.producerIndexOfThis[r]);for(;t.producerNode.length>t.nextProducerIndex;)t.producerNode.pop(),t.producerLastReadVersion.pop(),t.producerIndexOfThis.pop()}}function na(t){et(t);for(let e=0;e<t.producerNode.length;e++){const r=t.producerNode[e],n=t.producerLastReadVersion[e];if(n!==r.version||(Un(r),n!==r.version))return!0}return!1}function Fn(t,e,r){var n;if(cs(t),et(t),t.liveConsumerNode.length===0){(n=t.watched)==null||n.call(t.wrapper);for(let s=0;s<t.producerNode.length;s++)t.producerIndexOfThis[s]=Fn(t.producerNode[s],t,s)}return t.liveConsumerIndexOfThis.push(r),t.liveConsumerNode.push(e)-1}function cr(t,e){var r;if(cs(t),et(t),typeof ngDevMode<"u"&&ngDevMode&&e>=t.liveConsumerNode.length)throw new Error(`Assertion error: active consumer index ${e} is out of bounds of ${t.liveConsumerNode.length} consumers)`);if(t.liveConsumerNode.length===1){(r=t.unwatched)==null||r.call(t.wrapper);for(let s=0;s<t.producerNode.length;s++)cr(t.producerNode[s],t.producerIndexOfThis[s])}const n=t.liveConsumerNode.length-1;if(t.liveConsumerNode[e]=t.liveConsumerNode[n],t.liveConsumerIndexOfThis[e]=t.liveConsumerIndexOfThis[n],t.liveConsumerNode.length--,t.liveConsumerIndexOfThis.length--,e<t.liveConsumerNode.length){const s=t.liveConsumerIndexOfThis[e],i=t.liveConsumerNode[e];et(i),i.producerIndexOfThis[s]=e}}function Wr(t){var e;return t.consumerIsAlwaysLive||(((e=t==null?void 0:t.liveConsumerNode)==null?void 0:e.length)??0)>0}function et(t){t.producerNode??(t.producerNode=[]),t.producerIndexOfThis??(t.producerIndexOfThis=[]),t.producerLastReadVersion??(t.producerLastReadVersion=[])}function cs(t){t.liveConsumerNode??(t.liveConsumerNode=[]),t.liveConsumerIndexOfThis??(t.liveConsumerIndexOfThis=[])}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Bn(t){if(Un(t),lr(t),t.value===qr)throw t.error;return t.value}function ia(t){const e=Object.create(aa);e.computation=t;const r=()=>Bn(e);return r[Jt]=e,r}const Mr=Symbol("UNSET"),zr=Symbol("COMPUTING"),qr=Symbol("ERRORED"),aa={...ls,value:Mr,dirty:!0,error:null,equal:zn,producerMustRecompute(t){return t.value===Mr||t.value===zr},producerRecomputeValue(t){if(t.value===zr)throw new Error("Detected cycle in computations.");const e=t.value;t.value=zr;const r=ra(t);let n,s=!1;try{n=t.computation.call(t.wrapper),s=e!==Mr&&e!==qr&&t.equal.call(t.wrapper,e,n)}catch(i){n=qr,t.error=i}finally{sa(t,r)}if(s){t.value=e;return}t.value=n,t.version++}};/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function oa(){throw new Error}let la=oa;function ca(){la()}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function ua(t){const e=Object.create(ha);e.value=t;const r=()=>(lr(e),e.value);return r[Jt]=e,r}function da(){return lr(this),this.value}function pa(t,e){ea()||ca(),t.equal.call(t.wrapper,t.value,e)||(t.value=e,fa(t))}const ha={...ls,equal:zn,value:void 0};function fa(t){t.version++,Ji(),Hn(t)}/**
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
 */const q=Symbol("node");var ye;(t=>{var e,r,n,s;class i{constructor(l,p={}){Wt(this,r),Ir(this,e);const h=ua(l)[Jt];if(this[q]=h,h.wrapper=this,p){const m=p.equals;m&&(h.equal=m),h.watched=p[t.subtle.watched],h.unwatched=p[t.subtle.unwatched]}}get(){if(!(0,t.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.get");return da.call(this[q])}set(l){if(!(0,t.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.set");if(Qi())throw new Error("Writes to signals not permitted during Watcher callback");const p=this[q];pa(p,l)}}e=q,r=new WeakSet,t.isState=c=>typeof c=="object"&&Lr(r,c),t.State=i;class o{constructor(l,p){Wt(this,s),Ir(this,n);const h=ia(l)[Jt];if(h.consumerAllowSignalWrites=!0,this[q]=h,h.wrapper=this,p){const m=p.equals;m&&(h.equal=m),h.watched=p[t.subtle.watched],h.unwatched=p[t.subtle.unwatched]}}get(){if(!(0,t.isComputed)(this))throw new TypeError("Wrong receiver type for Signal.Computed.prototype.get");return Bn(this[q])}}n=q,s=new WeakSet,t.isComputed=c=>typeof c=="object"&&Lr(s,c),t.Computed=o,(c=>{var l,p,d,h;function m(T){let x,v=null;try{v=Qe(null),x=T()}finally{Qe(v)}return x}c.untrack=m;function R(T){var x;if(!(0,t.isComputed)(T)&&!(0,t.isWatcher)(T))throw new TypeError("Called introspectSources without a Computed or Watcher argument");return((x=T[q].producerNode)==null?void 0:x.map(v=>v.wrapper))??[]}c.introspectSources=R;function g(T){var x;if(!(0,t.isComputed)(T)&&!(0,t.isState)(T))throw new TypeError("Called introspectSinks without a Signal argument");return((x=T[q].liveConsumerNode)==null?void 0:x.map(v=>v.wrapper))??[]}c.introspectSinks=g;function Y(T){if(!(0,t.isComputed)(T)&&!(0,t.isState)(T))throw new TypeError("Called hasSinks without a Signal argument");const x=T[q].liveConsumerNode;return x?x.length>0:!1}c.hasSinks=Y;function E(T){if(!(0,t.isComputed)(T)&&!(0,t.isWatcher)(T))throw new TypeError("Called hasSources without a Computed or Watcher argument");const x=T[q].producerNode;return x?x.length>0:!1}c.hasSources=E;class se{constructor(x){Wt(this,p),Wt(this,d),Ir(this,l);let v=Object.create(ls);v.wrapper=this,v.consumerMarkedDirty=x,v.consumerIsAlwaysLive=!0,v.consumerAllowSignalWrites=!1,v.producerNode=[],this[q]=v}watch(...x){if(!(0,t.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");an(this,d,h).call(this,x);const v=this[q];v.dirty=!1;const S=Qe(v);for(const ne of x)lr(ne[q]);Qe(S)}unwatch(...x){if(!(0,t.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");an(this,d,h).call(this,x);const v=this[q];et(v);for(let S=v.producerNode.length-1;S>=0;S--)if(x.includes(v.producerNode[S].wrapper)){cr(v.producerNode[S],v.producerIndexOfThis[S]);const ne=v.producerNode.length-1;if(v.producerNode[S]=v.producerNode[ne],v.producerIndexOfThis[S]=v.producerIndexOfThis[ne],v.producerNode.length--,v.producerIndexOfThis.length--,v.nextProducerIndex--,S<v.producerNode.length){const lt=v.producerIndexOfThis[S],ct=v.producerNode[S];cs(ct),ct.liveConsumerIndexOfThis[lt]=S}}}getPending(){if(!(0,t.isWatcher)(this))throw new TypeError("Called getPending without Watcher receiver");return this[q].producerNode.filter(v=>v.dirty).map(v=>v.wrapper)}}l=q,p=new WeakSet,d=new WeakSet,h=function(T){for(const x of T)if(!(0,t.isComputed)(x)&&!(0,t.isState)(x))throw new TypeError("Called watch/unwatch without a Computed or State argument")},t.isWatcher=T=>Lr(p,T),c.Watcher=se;function ee(){var T;return(T=Xi())==null?void 0:T.wrapper}c.currentComputed=ee,c.watched=Symbol("watched"),c.unwatched=Symbol("unwatched")})(t.subtle||(t.subtle={}))})(ye||(ye={}));/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const ga=Symbol("SignalWatcherBrand"),ma=new FinalizationRegistry((({watcher:t,signal:e})=>{t.unwatch(e)})),on=new WeakMap;function jn(t){return t[ga]===!0?(console.warn("SignalWatcher should not be applied to the same class more than once."),t):class extends t{constructor(){super(...arguments),this._$St=new ye.State(0),this._$Si=!1,this._$So=!0,this._$Sh=new Set}_$Sl(){if(this._$Su!==void 0)return;this._$Sv=new ye.Computed((()=>{this._$St.get(),super.performUpdate()}));const e=this._$Su=new ye.subtle.Watcher((function(){const r=on.get(this);r!==void 0&&(r._$Si===!1&&r.requestUpdate(),this.watch())}));on.set(e,this),ma.register(this,{watcher:e,signal:this._$Sv}),e.watch(this._$Sv)}_$Sp(){this._$Su!==void 0&&(this._$Su.unwatch(this._$Sv),this._$Sv=void 0,this._$Su=void 0)}performUpdate(){this.isUpdatePending&&(this._$Sl(),this._$Si=!0,this._$St.set(this._$St.get()+1),this._$Si=!1,this._$Sv.get())}update(e){try{this._$So?(this._$So=!1,super.update(e)):this._$Sh.forEach((r=>r.commit()))}finally{this.isUpdatePending=!1,this._$Sh.clear()}}requestUpdate(e,r,n){this._$So=!0,super.requestUpdate(e,r,n)}connectedCallback(){super.connectedCallback(),this.requestUpdate()}disconnectedCallback(){super.disconnectedCallback(),queueMicrotask((()=>{this.isConnected===!1&&this._$Sp()}))}_(e){this._$Sh.add(e);const r=this._$So;this.requestUpdate(),this._$So=r}m(e){this._$Sh.delete(e)}}}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const ba={CHILD:2},va=t=>(...e)=>({_$litDirective$:t,values:e});let ya=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,r,n){this._$Ct=e,this._$AM=r,this._$Ci=n}_$AS(e,r){return this.update(e,r)}update(e,r){return this.render(...r)}};/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */ye.State;ye.Computed;const st=(t,e)=>new ye.State(t,e),wa=(t,e)=>new ye.Computed(t,e);class xa{constructor(e="/ws/deep"){this.ws=null,this.handlers=new Set,this.reconnectDelay=1e3,this.maxDelay=15e3,this.closedByUser=!1,this.status="closed";const r=location.protocol==="https:"?"wss":"ws";this.url=`${r}://${location.host}${e}`}connect(){this.closedByUser=!1,this.status="connecting",this.ws=new WebSocket(this.url),this.ws.onopen=()=>{this.status="open",this.reconnectDelay=1e3,this.emit({type:"_socket_open"})},this.ws.onmessage=e=>{try{this.emit(JSON.parse(e.data))}catch{}},this.ws.onclose=()=>{this.status="closed",this.emit({type:"_socket_close"}),this.closedByUser||this.scheduleReconnect()},this.ws.onerror=()=>{var e;return(e=this.ws)==null?void 0:e.close()}}scheduleReconnect(){setTimeout(()=>this.connect(),this.reconnectDelay),this.reconnectDelay=Math.min(this.reconnectDelay*1.6,this.maxDelay)}send(e){var r;((r=this.ws)==null?void 0:r.readyState)===WebSocket.OPEN&&this.ws.send(JSON.stringify(e))}on(e){return this.handlers.add(e),()=>this.handlers.delete(e)}emit(e){for(const r of this.handlers)r(e)}close(){var e;this.closedByUser=!0,(e=this.ws)==null||e.close()}}const Gr=new xa;let Yr=1;const Vr=st("closed"),te=st([]),Te=st(!1),er=st([]),Wn=st("—"),ka=st(""),_a=wa(()=>te.get().some(t=>t.streaming));function $a(t,e=null){!t.trim()&&!e||(te.set([...te.get(),{id:Yr++,role:"user",text:t,image:e}]),Te.set(!0),er.set([]),Gr.send({type:"chat",text:t,mode:"auto",image:e}))}function Ta(){return te.get().find(t=>t.streaming)}function ln(t){te.set(te.get().map(e=>e.streaming?{...e,...t}:e))}function Sa(t){switch(t.type){case"_socket_open":Vr.set("open");break;case"_socket_close":Vr.set("closed");break;case"thinking":Te.set(!0);break;case"response_start":Te.set(!0);break;case"token":{Te.set(!1);const e=String(t.content??"");Ta()?te.set(te.get().map(n=>n.streaming?{...n,text:n.text+e}:n)):te.set([...te.get(),{id:Yr++,role:"ai",text:e,streaming:!0}]);break}case"response_end":{Te.set(!1);const e=t;e.model&&Wn.set(e.model),ln({streaming:!1,model:e.model,latency:e.latency});break}case"reasoning":{const e=t.step;e&&er.set([...er.get(),e]);break}case"error":{Te.set(!1),ln({streaming:!1}),te.set([...te.get(),{id:Yr++,role:"ai",text:`⚠ ${t.message??"error"}`}]);break}default:ka.set(t.type)}}let cn=!1;function Aa(){cn||(cn=!0,Gr.on(t=>Sa(t)),Gr.connect())}async function nt(t){const e=await fetch(t);if(!e.ok)throw new Error(`${t} → ${e.status}`);return await e.json()}const Ea=()=>nt("/api/status"),Ra=(t=!1)=>nt(`/api/providers/health${t?"?force=true":""}`),Ca=()=>nt("/api/chem/table"),Oa=t=>nt(`/api/chem/element/${t}`),Pa=()=>nt("/api/physics/constants"),Da=t=>nt("/api/physics/formulas");async function un(t){const e=new FormData;return e.append("file",t,t.name),await(await fetch("/api/knowledge/ingest",{method:"POST",body:e})).json()}var Na=Object.defineProperty,Ia=Object.getOwnPropertyDescriptor,qn=(t,e,r,n)=>{for(var s=n>1?void 0:n?Ia(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&Na(e,r,s),s};let La=0,qt=null;function Z(t,e="info",r=6e3){qt||(qt=document.createElement("ds-toast-host"),document.body.appendChild(qt)),qt.push({id:++La,text:t,kind:e},r)}let tr=class extends X{constructor(){super(...arguments),this.items=[]}push(t,e){this.items=[...this.items,t],setTimeout(()=>this.dismiss(t.id),e)}dismiss(t){this.items=this.items.filter(e=>e.id!==t)}render(){return _`${this.items.map(t=>_`
        <div class="toast ${t.kind}">
          <span>${t.text}</span>
          <button class="x" @click=${()=>this.dismiss(t.id)} aria-label="Dismiss">✕</button>
        </div>
      `)}`}};tr.styles=ae`
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
  `;qn([re()],tr.prototype,"items",2);tr=qn([oe("ds-toast-host")],tr);const rr=[];function it(t){rr.some(e=>e.id===t.id)||rr.push(t)}function Ma(t,e){const r=t.toLowerCase(),n=e.toLowerCase();let s=0,i=0;for(const o of r){const c=n.indexOf(o,s);if(c===-1)return-1;i+=c-s+(c===s?0:2),s=c+1}return i}function za(t){return t.trim()?rr.map(e=>({c:e,s:Ma(t,e.label)})).filter(e=>e.s>=0).sort((e,r)=>e.s-r.s).map(e=>e.c):rr}const us=t=>()=>{location.hash=t};it({id:"nav.chat",label:"Go to Chat",hint:"nav",run:us("home")});it({id:"nav.gallery",label:"Open Design Gallery",hint:"nav",run:us("gallery")});it({id:"nav.science",label:"Open Science (Periodic Table & Physics)",hint:"nav",run:us("science")});it({id:"nav.legacy",label:"Open Legacy UI (/ai)",hint:"nav",run:()=>{location.href="/ai"}});it({id:"sys.providers",label:"Check AI Provider Health",hint:"system",run:async()=>{try{const t=await Ra(!0),e=t.providers.filter(r=>r.configured&&!r.ok);e.length?Z(`${e.length} provider(s) down: ${e.map(r=>r.provider).join(", ")}`,"danger",9e3):Z(`All ${t.healthy}/${t.total} provider keys healthy`,"success")}catch{Z("Provider health check failed","danger")}}});it({id:"sys.screen",label:"Describe My Screen",hint:"vision",run:async()=>{Z("DEEP is looking at your screen…","info");try{const e=await(await fetch("/api/vision/screen",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({q:"Describe what's on this screen for Aryan, concisely."})})).json();e.ok?Z(String(e.description).slice(0,280),"success",14e3):Z(`Screen read failed: ${e.error}`,"danger")}catch{Z("Screen read failed","danger")}}});var Ua=Object.defineProperty,Ha=Object.getOwnPropertyDescriptor,ur=(t,e,r,n)=>{for(var s=n>1?void 0:n?Ha(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&Ua(e,r,s),s};let tt=class extends X{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return _`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};tt.styles=ae`
    :host { display: inline-block; }
    button {
      display: inline-flex;
      align-items: center;
      gap: var(--ds-space-2);
      font-family: var(--ds-font-sans);
      font-weight: 500;
      border-radius: var(--ds-radius-sm);
      border: 1px solid var(--ds-border);
      background: var(--ds-surface-2);
      color: var(--ds-text);
      cursor: pointer;
      transition:
        background var(--ds-dur-fast) var(--ds-ease-out),
        border-color var(--ds-dur-fast) var(--ds-ease-out),
        transform var(--ds-dur-fast) var(--ds-ease-spring);
    }
    button:hover:not(:disabled) { background: var(--ds-surface-3); transform: translateY(-1px); }
    button:active:not(:disabled) { transform: translateY(0); }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    button:focus-visible { outline: none; box-shadow: var(--ds-focus-ring); }

    .md { padding: var(--ds-space-2) var(--ds-space-4); font-size: var(--ds-text-sm); }
    .sm { padding: var(--ds-space-1) var(--ds-space-3); font-size: var(--ds-text-xs); }

    .primary {
      background: var(--ds-accent);
      border-color: var(--ds-accent);
      color: var(--ds-on-accent);
      font-weight: 600;
    }
    .primary:hover:not(:disabled) { background: var(--ds-accent); filter: brightness(1.1); box-shadow: var(--ds-glow); }
    .danger { border-color: rgba(229, 115, 106, 0.4); color: var(--ds-danger); background: rgba(229, 115, 106, 0.08); }
    .danger:hover:not(:disabled) { background: rgba(229, 115, 106, 0.16); }
  `;ur([le()],tt.prototype,"variant",2);ur([le()],tt.prototype,"size",2);ur([le({type:Boolean})],tt.prototype,"disabled",2);tt=ur([oe("ds-button")],tt);var Fa=Object.defineProperty,Ba=Object.getOwnPropertyDescriptor,ds=(t,e,r,n)=>{for(var s=n>1?void 0:n?Ba(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&Fa(e,r,s),s};let St=class extends X{constructor(){super(...arguments),this.heading="",this.variant="solid"}render(){return _`
      <section class=${this.variant}>
        ${this.heading?_`<header><span>${this.heading}</span><slot name="actions"></slot></header>`:""}
        <div class="body"><slot></slot></div>
      </section>
    `}};St.styles=ae`
    :host { display: block; }
    section {
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-2);
      overflow: hidden;
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    .solid { background: var(--ds-surface-1); }
    .glass {
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--ds-space-3) var(--ds-space-4);
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      font-weight: 600;
      letter-spacing: var(--ds-tracking-wide);
      color: var(--ds-text-soft);
      text-transform: uppercase;
    }
    .body { padding: var(--ds-space-4); }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @media (prefers-reduced-motion: reduce) { section { animation: none; } }
  `;ds([le()],St.prototype,"heading",2);ds([le()],St.prototype,"variant",2);St=ds([oe("ds-panel")],St);var ja=Object.defineProperty,Wa=Object.getOwnPropertyDescriptor,at=(t,e,r,n)=>{for(var s=n>1?void 0:n?Wa(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&ja(e,r,s),s};let Ae=class extends X{constructor(){super(...arguments),this.label="",this.placeholder="",this.value="",this.type="text"}onInput(){this.value=this.input.value,this.dispatchEvent(new CustomEvent("ds-input",{detail:this.value,bubbles:!0,composed:!0}))}onKeydown(t){t.key==="Enter"&&this.dispatchEvent(new CustomEvent("ds-submit",{detail:this.value,bubbles:!0,composed:!0}))}render(){return _`
      ${this.label?_`<label>${this.label}</label>`:""}
      <input
        .type=${this.type}
        .value=${this.value}
        placeholder=${this.placeholder}
        @input=${this.onInput}
        @keydown=${this.onKeydown}
      />
    `}};Ae.styles=ae`
    :host { display: block; }
    label {
      display: block;
      margin-bottom: var(--ds-space-1);
      font-size: var(--ds-text-xs);
      letter-spacing: var(--ds-tracking-wide);
      text-transform: uppercase;
      color: var(--ds-text-muted);
    }
    input {
      width: 100%;
      padding: var(--ds-space-2) var(--ds-space-3);
      font-family: var(--ds-font-sans);
      font-size: var(--ds-text-sm);
      color: var(--ds-text);
      background: var(--ds-surface-2);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-sm);
      transition: border-color var(--ds-dur-fast) var(--ds-ease-out);
    }
    input::placeholder { color: var(--ds-text-faint); }
    input:hover { border-color: var(--ds-border-strong); }
    input:focus { outline: none; border-color: var(--ds-border-accent); box-shadow: var(--ds-focus-ring); }
  `;at([le()],Ae.prototype,"label",2);at([le()],Ae.prototype,"placeholder",2);at([le()],Ae.prototype,"value",2);at([le()],Ae.prototype,"type",2);at([os("input")],Ae.prototype,"input",2);Ae=at([oe("ds-field")],Ae);var qa=Object.getOwnPropertyDescriptor,Ga=(t,e,r,n)=>{for(var s=n>1?void 0:n?qa(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=o(s)||s);return s};let Zr=class extends X{render(){return _`
      <h1>Design system gallery</h1>

      <ds-panel heading="Buttons">
        <div class="row">
          <ds-button variant="primary">Primary</ds-button>
          <ds-button>Ghost</ds-button>
          <ds-button variant="danger">Danger</ds-button>
          <ds-button variant="primary" size="sm">Small</ds-button>
          <ds-button disabled>Disabled</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Fields">
        <div class="row" style="align-items:end">
          <ds-field label="Name" placeholder="Type something…" style="flex:1"></ds-field>
          <ds-field label="Token" placeholder="••••" type="password" style="flex:1"></ds-field>
        </div>
      </ds-panel>

      <ds-panel heading="Toasts">
        <div class="row">
          <ds-button @click=${()=>Z("Saved successfully","success")}>Success</ds-button>
          <ds-button @click=${()=>Z("Heads up — informational","info")}>Info</ds-button>
          <ds-button variant="danger" @click=${()=>Z("Something failed","danger")}>Danger</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Surfaces" variant="glass">
        <p style="margin:0;color:var(--ds-text-soft)">This panel uses the glass variant.</p>
      </ds-panel>

      <ds-panel heading="Color tokens">
        <div class="swatches">
          ${["--ds-bg","--ds-surface-1","--ds-surface-2","--ds-surface-3","--ds-accent","--ds-success","--ds-warning","--ds-danger","--ds-info"].map(t=>_`<div class="sw" style="background: var(${t})">${t.slice(5)}</div>`)}
        </div>
      </ds-panel>
    `}};Zr.styles=ae`
    :host {
      display: grid;
      gap: var(--ds-space-5);
      padding: var(--ds-space-6);
      max-width: 860px;
      margin: 0 auto;
    }
    .row { display: flex; gap: var(--ds-space-3); align-items: center; flex-wrap: wrap; }
    h1 { font-size: var(--ds-text-xl); margin: 0; }
    .swatches { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; }
    .sw {
      width: 72px; height: 48px;
      border-radius: var(--ds-radius-sm);
      border: 1px solid var(--ds-border);
      display: grid; place-items: end start;
      padding: 4px; font-size: 9px; color: var(--ds-text-muted);
      font-family: var(--ds-font-mono);
    }
  `;Zr=Ga([oe("ds-gallery")],Zr);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class Kr extends ya{constructor(e){if(super(e),this.it=H,e.type!==ba.CHILD)throw Error(this.constructor.directiveName+"() can only be used in child bindings")}render(e){if(e===H||e==null)return this._t=void 0,this.it=e;if(e===Le)return e;if(typeof e!="string")throw Error(this.constructor.directiveName+"() called with a non-string value");if(e===this.it)return this._t;this.it=e;const r=[e];return r.raw=r,this._t={_$litType$:this.constructor.resultType,strings:r,values:[]}}}Kr.directiveName="unsafeHTML",Kr.resultType=1;const Ya=va(Kr);function ps(){return{async:!1,breaks:!1,extensions:null,gfm:!0,hooks:null,pedantic:!1,renderer:null,silent:!1,tokenizer:null,walkTokens:null}}var He=ps();function Gn(t){He=t}var Pe={exec:()=>null};function Ye(t){let e=[];return r=>{let n=Math.max(0,Math.min(3,r-1)),s=e[n];return s||(s=t(n),e[n]=s),s}}function A(t,e=""){let r=typeof t=="string"?t:t.source,n={replace:(s,i)=>{let o=typeof i=="string"?i:i.source;return o=o.replace(K.caret,"$1"),r=r.replace(s,o),n},getRegex:()=>new RegExp(r,e)};return n}var Va=((t="")=>{try{return!!new RegExp("(?<=1)(?<!1)"+t)}catch{return!1}})(),K={codeRemoveIndent:/^(?: {1,4}| {0,3}\t)/gm,outputLinkReplace:/\\([\[\]])/g,indentCodeCompensation:/^(\s+)(?:```)/,beginningSpace:/^\s+/,endingHash:/#$/,startingSpaceChar:/^ /,endingSpaceChar:/ $/,nonSpaceChar:/[^ ]/,newLineCharGlobal:/\n/g,tabCharGlobal:/\t/g,multipleSpaceGlobal:/\s+/g,blankLine:/^[ \t]*$/,doubleBlankLine:/\n[ \t]*\n[ \t]*$/,blockquoteStart:/^ {0,3}>/,blockquoteSetextReplace:/\n {0,3}((?:=+|-+) *)(?=\n|$)/g,blockquoteSetextReplace2:/^ {0,3}>[ \t]?/gm,listReplaceNesting:/^ {1,4}(?=( {4})*[^ ])/g,listIsTask:/^\[[ xX]\] +\S/,listReplaceTask:/^\[[ xX]\] +/,listTaskCheckbox:/\[[ xX]\]/,anyLine:/\n.*\n/,hrefBrackets:/^<(.*)>$/,tableDelimiter:/[:|]/,tableAlignChars:/^\||\| *$/g,tableRowBlankLine:/\n[ \t]*$/,tableAlignRight:/^ *-+: *$/,tableAlignCenter:/^ *:-+: *$/,tableAlignLeft:/^ *:-+ *$/,startATag:/^<a /i,endATag:/^<\/a>/i,startPreScriptTag:/^<(pre|code|kbd|script)(\s|>)/i,endPreScriptTag:/^<\/(pre|code|kbd|script)(\s|>)/i,startAngleBracket:/^</,endAngleBracket:/>$/,pedanticHrefTitle:/^([^'"]*[^\s])\s+(['"])(.*)\2/,unicodeAlphaNumeric:/[\p{L}\p{N}]/u,escapeTest:/[&<>"']/,escapeReplace:/[&<>"']/g,escapeTestNoEncode:/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,escapeReplaceNoEncode:/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,caret:/(^|[^\[])\^/g,percentDecode:/%25/g,findPipe:/\|/g,splitPipe:/ \|/,slashPipe:/\\\|/g,carriageReturn:/\r\n|\r/g,spaceLine:/^ +$/gm,notSpaceStart:/^\S*/,endingNewline:/\n$/,listItemRegex:t=>new RegExp(`^( {0,3}${t})((?:[	 ][^\\n]*)?(?:\\n|$))`),nextBulletRegex:Ye(t=>new RegExp(`^ {0,${t}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),hrRegex:Ye(t=>new RegExp(`^ {0,${t}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),fencesBeginRegex:Ye(t=>new RegExp(`^ {0,${t}}(?:\`\`\`|~~~)`)),headingBeginRegex:Ye(t=>new RegExp(`^ {0,${t}}#`)),htmlBeginRegex:Ye(t=>new RegExp(`^ {0,${t}}<(?:[a-z].*>|!--)`,"i")),blockquoteBeginRegex:Ye(t=>new RegExp(`^ {0,${t}}>`))},Za=/^(?:[ \t]*(?:\n|$))+/,Ka=/^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/,Xa=/^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/,Ct=/^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/,Qa=/^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/,hs=/ {0,3}(?:[*+-]|\d{1,9}[.)])/,Yn=/^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/,Vn=A(Yn).replace(/bull/g,hs).replace(/blockCode/g,/(?: {4}| {0,3}\t)/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).replace(/\|table/g,"").getRegex(),Ja=A(Yn).replace(/bull/g,hs).replace(/blockCode/g,/(?: {4}| {0,3}\t)/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).replace(/table/g,/ {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(),fs=/^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/,eo=/^[^\n]+/,gs=/(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/,to=A(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label",gs).replace("title",/(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(),ro=A(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g,hs).getRegex(),dr="address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul",ms=/<!--(?:-?>|[\s\S]*?(?:-->|$))/,so=A("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))","i").replace("comment",ms).replace("tag",dr).replace("attribute",/ +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(),Zn=A(fs).replace("hr",Ct).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("|lheading","").replace("|table","").replace("blockquote"," {0,3}>").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",dr).getRegex(),no=A(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph",Zn).getRegex(),bs={blockquote:no,code:Ka,def:to,fences:Xa,heading:Qa,hr:Ct,html:so,lheading:Vn,list:ro,newline:Za,paragraph:Zn,table:Pe,text:eo},dn=A("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr",Ct).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("blockquote"," {0,3}>").replace("code","(?: {4}| {0,3}	)[^\\n]").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",dr).getRegex(),io={...bs,lheading:Ja,table:dn,paragraph:A(fs).replace("hr",Ct).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("|lheading","").replace("table",dn).replace("blockquote"," {0,3}>").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",dr).getRegex()},ao={...bs,html:A(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace("comment",ms).replace(/tag/g,"(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),def:/^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,heading:/^(#{1,6})(.*)(?:\n+|$)/,fences:Pe,lheading:/^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,paragraph:A(fs).replace("hr",Ct).replace("heading",` *#{1,6} *[^
]`).replace("lheading",Vn).replace("|table","").replace("blockquote"," {0,3}>").replace("|fences","").replace("|list","").replace("|html","").replace("|tag","").getRegex()},oo=/^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/,lo=/^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/,Kn=/^( {2,}|\\)\n(?!\s*$)/,co=/^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/,ot=/[\p{P}\p{S}]/u,pr=/[\s\p{P}\p{S}]/u,vs=/[^\s\p{P}\p{S}]/u,uo=A(/^((?![*_])punctSpace)/,"u").replace(/punctSpace/g,pr).getRegex(),Xn=/(?!~)[\p{P}\p{S}]/u,po=/(?!~)[\s\p{P}\p{S}]/u,ho=/(?:[^\s\p{P}\p{S}]|~)/u,fo=A(/link|precode-code|html/,"g").replace("link",/\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-",Va?"(?<!`)()":"(^^|[^`])").replace("code",/(?<b>`+)[^`]+\k<b>(?!`)/).replace("html",/<(?! )[^<>]*?>/).getRegex(),Qn=/^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/,go=A(Qn,"u").replace(/punct/g,ot).getRegex(),mo=A(Qn,"u").replace(/punct/g,Xn).getRegex(),Jn="^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)",bo=A(Jn,"gu").replace(/notPunctSpace/g,vs).replace(/punctSpace/g,pr).replace(/punct/g,ot).getRegex(),vo=A(Jn,"gu").replace(/notPunctSpace/g,ho).replace(/punctSpace/g,po).replace(/punct/g,Xn).getRegex(),yo=A("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)","gu").replace(/notPunctSpace/g,vs).replace(/punctSpace/g,pr).replace(/punct/g,ot).getRegex(),wo=A(/^~~?(?:((?!~)punct)|[^\s~])/,"u").replace(/punct/g,ot).getRegex(),xo="^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)",ko=A(xo,"gu").replace(/notPunctSpace/g,vs).replace(/punctSpace/g,pr).replace(/punct/g,ot).getRegex(),_o=A(/\\(punct)/,"gu").replace(/punct/g,ot).getRegex(),$o=A(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme",/[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email",/[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(),To=A(ms).replace("(?:-->|$)","-->").getRegex(),So=A("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment",To).replace("attribute",/\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(),sr=/(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/,Ao=A(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label",sr).replace("href",/<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*/).replace("title",/"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(),ei=A(/^!?\[(label)\]\[(ref)\]/).replace("label",sr).replace("ref",gs).getRegex(),ti=A(/^!?\[(ref)\](?:\[\])?/).replace("ref",gs).getRegex(),Eo=A("reflink|nolink(?!\\()","g").replace("reflink",ei).replace("nolink",ti).getRegex(),pn=/[hH][tT][tT][pP][sS]?|[fF][tT][pP]/,ys={_backpedal:Pe,anyPunctuation:_o,autolink:$o,blockSkip:fo,br:Kn,code:lo,del:Pe,delLDelim:Pe,delRDelim:Pe,emStrongLDelim:go,emStrongRDelimAst:bo,emStrongRDelimUnd:yo,escape:oo,link:Ao,nolink:ti,punctuation:uo,reflink:ei,reflinkSearch:Eo,tag:So,text:co,url:Pe},Ro={...ys,link:A(/^!?\[(label)\]\((.*?)\)/).replace("label",sr).getRegex(),reflink:A(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label",sr).getRegex()},Xr={...ys,emStrongRDelimAst:vo,emStrongLDelim:mo,delLDelim:wo,delRDelim:ko,url:A(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol",pn).replace("email",/[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),_backpedal:/(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,del:/^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,text:A(/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol",pn).getRegex()},Co={...Xr,br:A(Kn).replace("{2,}","*").getRegex(),text:A(Xr.text).replace("\\b_","\\b_| {2,}\\n").replace(/\{2,\}/g,"*").getRegex()},Gt={normal:bs,gfm:io,pedantic:ao},mt={normal:ys,gfm:Xr,breaks:Co,pedantic:Ro},Oo={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"},hn=t=>Oo[t];function ge(t,e){if(e){if(K.escapeTest.test(t))return t.replace(K.escapeReplace,hn)}else if(K.escapeTestNoEncode.test(t))return t.replace(K.escapeReplaceNoEncode,hn);return t}function fn(t){try{t=encodeURI(t).replace(K.percentDecode,"%")}catch{return null}return t}function gn(t,e){var i;let r=t.replace(K.findPipe,(o,c,l)=>{let p=!1,d=c;for(;--d>=0&&l[d]==="\\";)p=!p;return p?"|":" |"}),n=r.split(K.splitPipe),s=0;if(n[0].trim()||n.shift(),n.length>0&&!((i=n.at(-1))!=null&&i.trim())&&n.pop(),e)if(n.length>e)n.splice(e);else for(;n.length<e;)n.push("");for(;s<n.length;s++)n[s]=n[s].trim().replace(K.slashPipe,"|");return n}function _e(t,e,r){let n=t.length;if(n===0)return"";let s=0;for(;s<n&&t.charAt(n-s-1)===e;)s++;return t.slice(0,n-s)}function mn(t){let e=t.split(`
`),r=e.length-1;for(;r>=0&&K.blankLine.test(e[r]);)r--;return e.length-r<=2?t:e.slice(0,r+1).join(`
`)}function Po(t,e){if(t.indexOf(e[1])===-1)return-1;let r=0;for(let n=0;n<t.length;n++)if(t[n]==="\\")n++;else if(t[n]===e[0])r++;else if(t[n]===e[1]&&(r--,r<0))return n;return r>0?-2:-1}function Do(t,e=0){let r=e,n="";for(let s of t)if(s==="	"){let i=4-r%4;n+=" ".repeat(i),r+=i}else n+=s,r++;return n}function bn(t,e,r,n,s){let i=e.href,o=e.title||null,c=t[1].replace(s.other.outputLinkReplace,"$1");n.state.inLink=!0;let l={type:t[0].charAt(0)==="!"?"image":"link",raw:r,href:i,title:o,text:c,tokens:n.inlineTokens(c)};return n.state.inLink=!1,l}function No(t,e,r){let n=t.match(r.other.indentCodeCompensation);if(n===null)return e;let s=n[1];return e.split(`
`).map(i=>{let o=i.match(r.other.beginningSpace);if(o===null)return i;let[c]=o;return c.length>=s.length?i.slice(s.length):i}).join(`
`)}var nr=class{constructor(t){O(this,"options");O(this,"rules");O(this,"lexer");this.options=t||He}space(t){let e=this.rules.block.newline.exec(t);if(e&&e[0].length>0)return{type:"space",raw:e[0]}}code(t){let e=this.rules.block.code.exec(t);if(e){let r=this.options.pedantic?e[0]:mn(e[0]),n=r.replace(this.rules.other.codeRemoveIndent,"");return{type:"code",raw:r,codeBlockStyle:"indented",text:n}}}fences(t){let e=this.rules.block.fences.exec(t);if(e){let r=e[0],n=No(r,e[3]||"",this.rules);return{type:"code",raw:r,lang:e[2]?e[2].trim().replace(this.rules.inline.anyPunctuation,"$1"):e[2],text:n}}}heading(t){let e=this.rules.block.heading.exec(t);if(e){let r=e[2].trim();if(this.rules.other.endingHash.test(r)){let n=_e(r,"#");(this.options.pedantic||!n||this.rules.other.endingSpaceChar.test(n))&&(r=n.trim())}return{type:"heading",raw:_e(e[0],`
`),depth:e[1].length,text:r,tokens:this.lexer.inline(r)}}}hr(t){let e=this.rules.block.hr.exec(t);if(e)return{type:"hr",raw:_e(e[0],`
`)}}blockquote(t){let e=this.rules.block.blockquote.exec(t);if(e){let r=_e(e[0],`
`).split(`
`),n="",s="",i=[];for(;r.length>0;){let o=!1,c=[],l;for(l=0;l<r.length;l++)if(this.rules.other.blockquoteStart.test(r[l]))c.push(r[l]),o=!0;else if(!o)c.push(r[l]);else break;r=r.slice(l);let p=c.join(`
`),d=p.replace(this.rules.other.blockquoteSetextReplace,`
    $1`).replace(this.rules.other.blockquoteSetextReplace2,"");n=n?`${n}
${p}`:p,s=s?`${s}
${d}`:d;let h=this.lexer.state.top;if(this.lexer.state.top=!0,this.lexer.blockTokens(d,i,!0),this.lexer.state.top=h,r.length===0)break;let m=i.at(-1);if((m==null?void 0:m.type)==="code")break;if((m==null?void 0:m.type)==="blockquote"){let R=m,g=R.raw+`
`+r.join(`
`),Y=this.blockquote(g);i[i.length-1]=Y,n=n.substring(0,n.length-R.raw.length)+Y.raw,s=s.substring(0,s.length-R.text.length)+Y.text;break}else if((m==null?void 0:m.type)==="list"){let R=m,g=R.raw+`
`+r.join(`
`),Y=this.list(g);i[i.length-1]=Y,n=n.substring(0,n.length-m.raw.length)+Y.raw,s=s.substring(0,s.length-R.raw.length)+Y.raw,r=g.substring(i.at(-1).raw.length).split(`
`);continue}}return{type:"blockquote",raw:n,tokens:i,text:s}}}list(t){let e=this.rules.block.list.exec(t);if(e){let r=e[1].trim(),n=r.length>1,s={type:"list",raw:"",ordered:n,start:n?+r.slice(0,-1):"",loose:!1,items:[]};r=n?`\\d{1,9}\\${r.slice(-1)}`:`\\${r}`,this.options.pedantic&&(r=n?r:"[*+-]");let i=this.rules.other.listItemRegex(r),o=!1;for(;t;){let l=!1,p="",d="";if(!(e=i.exec(t))||this.rules.block.hr.test(t))break;p=e[0],t=t.substring(p.length);let h=Do(e[2].split(`
`,1)[0],e[1].length),m=t.split(`
`,1)[0],R=!h.trim(),g=0;if(this.options.pedantic?(g=2,d=h.trimStart()):R?g=e[1].length+1:(g=h.search(this.rules.other.nonSpaceChar),g=g>4?1:g,d=h.slice(g),g+=e[1].length),R&&this.rules.other.blankLine.test(m)&&(p+=m+`
`,t=t.substring(m.length+1),l=!0),!l){let Y=this.rules.other.nextBulletRegex(g),E=this.rules.other.hrRegex(g),se=this.rules.other.fencesBeginRegex(g),ee=this.rules.other.headingBeginRegex(g),T=this.rules.other.htmlBeginRegex(g),x=this.rules.other.blockquoteBeginRegex(g);for(;t;){let v=t.split(`
`,1)[0],S;if(m=v,this.options.pedantic?(m=m.replace(this.rules.other.listReplaceNesting,"  "),S=m):S=m.replace(this.rules.other.tabCharGlobal,"    "),se.test(m)||ee.test(m)||T.test(m)||x.test(m)||Y.test(m)||E.test(m))break;if(S.search(this.rules.other.nonSpaceChar)>=g||!m.trim())d+=`
`+S.slice(g);else{if(R||h.replace(this.rules.other.tabCharGlobal,"    ").search(this.rules.other.nonSpaceChar)>=4||se.test(h)||ee.test(h)||E.test(h))break;d+=`
`+m}R=!m.trim(),p+=v+`
`,t=t.substring(v.length+1),h=S.slice(g)}}s.loose||(o?s.loose=!0:this.rules.other.doubleBlankLine.test(p)&&(o=!0)),s.items.push({type:"list_item",raw:p,task:!!this.options.gfm&&this.rules.other.listIsTask.test(d),loose:!1,text:d,tokens:[]}),s.raw+=p}let c=s.items.at(-1);if(c)c.raw=c.raw.trimEnd(),c.text=c.text.trimEnd();else return;s.raw=s.raw.trimEnd();for(let l of s.items){this.lexer.state.top=!1,l.tokens=this.lexer.blockTokens(l.text,[]);let p=l.tokens[0];if(l.task&&((p==null?void 0:p.type)==="text"||(p==null?void 0:p.type)==="paragraph")){l.text=l.text.replace(this.rules.other.listReplaceTask,""),p.raw=p.raw.replace(this.rules.other.listReplaceTask,""),p.text=p.text.replace(this.rules.other.listReplaceTask,"");for(let h=this.lexer.inlineQueue.length-1;h>=0;h--)if(this.rules.other.listIsTask.test(this.lexer.inlineQueue[h].src)){this.lexer.inlineQueue[h].src=this.lexer.inlineQueue[h].src.replace(this.rules.other.listReplaceTask,"");break}let d=this.rules.other.listTaskCheckbox.exec(l.raw);if(d){let h={type:"checkbox",raw:d[0]+" ",checked:d[0]!=="[ ]"};l.checked=h.checked,s.loose?l.tokens[0]&&["paragraph","text"].includes(l.tokens[0].type)&&"tokens"in l.tokens[0]&&l.tokens[0].tokens?(l.tokens[0].raw=h.raw+l.tokens[0].raw,l.tokens[0].text=h.raw+l.tokens[0].text,l.tokens[0].tokens.unshift(h)):l.tokens.unshift({type:"paragraph",raw:h.raw,text:h.raw,tokens:[h]}):l.tokens.unshift(h)}}else l.task&&(l.task=!1);if(!s.loose){let d=l.tokens.filter(m=>m.type==="space"),h=d.length>0&&d.some(m=>this.rules.other.anyLine.test(m.raw));s.loose=h}}if(s.loose)for(let l of s.items){l.loose=!0;for(let p of l.tokens)p.type==="text"&&(p.type="paragraph")}return s}}html(t){let e=this.rules.block.html.exec(t);if(e){let r=mn(e[0]);return{type:"html",block:!0,raw:r,pre:e[1]==="pre"||e[1]==="script"||e[1]==="style",text:r}}}def(t){let e=this.rules.block.def.exec(t);if(e){let r=e[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal," "),n=e[2]?e[2].replace(this.rules.other.hrefBrackets,"$1").replace(this.rules.inline.anyPunctuation,"$1"):"",s=e[3]?e[3].substring(1,e[3].length-1).replace(this.rules.inline.anyPunctuation,"$1"):e[3];return{type:"def",tag:r,raw:_e(e[0],`
`),href:n,title:s}}}table(t){var o;let e=this.rules.block.table.exec(t);if(!e||!this.rules.other.tableDelimiter.test(e[2]))return;let r=gn(e[1]),n=e[2].replace(this.rules.other.tableAlignChars,"").split("|"),s=(o=e[3])!=null&&o.trim()?e[3].replace(this.rules.other.tableRowBlankLine,"").split(`
`):[],i={type:"table",raw:_e(e[0],`
`),header:[],align:[],rows:[]};if(r.length===n.length){for(let c of n)this.rules.other.tableAlignRight.test(c)?i.align.push("right"):this.rules.other.tableAlignCenter.test(c)?i.align.push("center"):this.rules.other.tableAlignLeft.test(c)?i.align.push("left"):i.align.push(null);for(let c=0;c<r.length;c++)i.header.push({text:r[c],tokens:this.lexer.inline(r[c]),header:!0,align:i.align[c]});for(let c of s)i.rows.push(gn(c,i.header.length).map((l,p)=>({text:l,tokens:this.lexer.inline(l),header:!1,align:i.align[p]})));return i}}lheading(t){let e=this.rules.block.lheading.exec(t);if(e){let r=e[1].trim();return{type:"heading",raw:_e(e[0],`
`),depth:e[2].charAt(0)==="="?1:2,text:r,tokens:this.lexer.inline(r)}}}paragraph(t){let e=this.rules.block.paragraph.exec(t);if(e){let r=e[1].charAt(e[1].length-1)===`
`?e[1].slice(0,-1):e[1];return{type:"paragraph",raw:e[0],text:r,tokens:this.lexer.inline(r)}}}text(t){let e=this.rules.block.text.exec(t);if(e)return{type:"text",raw:e[0],text:e[0],tokens:this.lexer.inline(e[0])}}escape(t){let e=this.rules.inline.escape.exec(t);if(e)return{type:"escape",raw:e[0],text:e[1]}}tag(t){let e=this.rules.inline.tag.exec(t);if(e)return!this.lexer.state.inLink&&this.rules.other.startATag.test(e[0])?this.lexer.state.inLink=!0:this.lexer.state.inLink&&this.rules.other.endATag.test(e[0])&&(this.lexer.state.inLink=!1),!this.lexer.state.inRawBlock&&this.rules.other.startPreScriptTag.test(e[0])?this.lexer.state.inRawBlock=!0:this.lexer.state.inRawBlock&&this.rules.other.endPreScriptTag.test(e[0])&&(this.lexer.state.inRawBlock=!1),{type:"html",raw:e[0],inLink:this.lexer.state.inLink,inRawBlock:this.lexer.state.inRawBlock,block:!1,text:e[0]}}link(t){let e=this.rules.inline.link.exec(t);if(e){let r=e[2].trim();if(!this.options.pedantic&&this.rules.other.startAngleBracket.test(r)){if(!this.rules.other.endAngleBracket.test(r))return;let i=_e(r.slice(0,-1),"\\");if((r.length-i.length)%2===0)return}else{let i=Po(e[2],"()");if(i===-2)return;if(i>-1){let o=(e[0].indexOf("!")===0?5:4)+e[1].length+i;e[2]=e[2].substring(0,i),e[0]=e[0].substring(0,o).trim(),e[3]=""}}let n=e[2],s="";if(this.options.pedantic){let i=this.rules.other.pedanticHrefTitle.exec(n);i&&(n=i[1],s=i[3])}else s=e[3]?e[3].slice(1,-1):"";return n=n.trim(),this.rules.other.startAngleBracket.test(n)&&(this.options.pedantic&&!this.rules.other.endAngleBracket.test(r)?n=n.slice(1):n=n.slice(1,-1)),bn(e,{href:n&&n.replace(this.rules.inline.anyPunctuation,"$1"),title:s&&s.replace(this.rules.inline.anyPunctuation,"$1")},e[0],this.lexer,this.rules)}}reflink(t,e){let r;if((r=this.rules.inline.reflink.exec(t))||(r=this.rules.inline.nolink.exec(t))){let n=(r[2]||r[1]).replace(this.rules.other.multipleSpaceGlobal," "),s=e[n.toLowerCase()];if(!s){let i=r[0].charAt(0);return{type:"text",raw:i,text:i}}return bn(r,s,r[0],this.lexer,this.rules)}}emStrong(t,e,r=""){let n=this.rules.inline.emStrongLDelim.exec(t);if(!(!n||!n[1]&&!n[2]&&!n[3]&&!n[4]||n[4]&&r.match(this.rules.other.unicodeAlphaNumeric))&&(!(n[1]||n[3])||!r||this.rules.inline.punctuation.exec(r))){let s=[...n[0]].length-1,i,o,c=s,l=0,p=n[0][0]==="*"?this.rules.inline.emStrongRDelimAst:this.rules.inline.emStrongRDelimUnd;for(p.lastIndex=0,e=e.slice(-1*t.length+s);(n=p.exec(e))!==null;){if(i=n[1]||n[2]||n[3]||n[4]||n[5]||n[6],!i)continue;if(o=[...i].length,n[3]||n[4]){c+=o;continue}else if((n[5]||n[6])&&s%3&&!((s+o)%3)){l+=o;continue}if(c-=o,c>0)continue;o=Math.min(o,o+c+l);let d=[...n[0]][0].length,h=t.slice(0,s+n.index+d+o);if(Math.min(s,o)%2){let R=h.slice(1,-1);return{type:"em",raw:h,text:R,tokens:this.lexer.inlineTokens(R)}}let m=h.slice(2,-2);return{type:"strong",raw:h,text:m,tokens:this.lexer.inlineTokens(m)}}}}codespan(t){let e=this.rules.inline.code.exec(t);if(e){let r=e[2].replace(this.rules.other.newLineCharGlobal," "),n=this.rules.other.nonSpaceChar.test(r),s=this.rules.other.startingSpaceChar.test(r)&&this.rules.other.endingSpaceChar.test(r);return n&&s&&(r=r.substring(1,r.length-1)),{type:"codespan",raw:e[0],text:r}}}br(t){let e=this.rules.inline.br.exec(t);if(e)return{type:"br",raw:e[0]}}del(t,e,r=""){let n=this.rules.inline.delLDelim.exec(t);if(n&&(!n[1]||!r||this.rules.inline.punctuation.exec(r))){let s=[...n[0]].length-1,i,o,c=s,l=this.rules.inline.delRDelim;for(l.lastIndex=0,e=e.slice(-1*t.length+s);(n=l.exec(e))!==null;){if(i=n[1]||n[2]||n[3]||n[4]||n[5]||n[6],!i||(o=[...i].length,o!==s))continue;if(n[3]||n[4]){c+=o;continue}if(c-=o,c>0)continue;o=Math.min(o,o+c);let p=[...n[0]][0].length,d=t.slice(0,s+n.index+p+o),h=d.slice(s,-s);return{type:"del",raw:d,text:h,tokens:this.lexer.inlineTokens(h)}}}}autolink(t){let e=this.rules.inline.autolink.exec(t);if(e){let r,n;return e[2]==="@"?(r=e[1],n="mailto:"+r):(r=e[1],n=r),{type:"link",raw:e[0],text:r,href:n,tokens:[{type:"text",raw:r,text:r}]}}}url(t){var r;let e;if(e=this.rules.inline.url.exec(t)){let n,s;if(e[2]==="@")n=e[0],s="mailto:"+n;else{let i;do i=e[0],e[0]=((r=this.rules.inline._backpedal.exec(e[0]))==null?void 0:r[0])??"";while(i!==e[0]);n=e[0],e[1]==="www."?s="http://"+e[0]:s=e[0]}return{type:"link",raw:e[0],text:n,href:s,tokens:[{type:"text",raw:n,text:n}]}}}inlineText(t){let e=this.rules.inline.text.exec(t);if(e){let r=this.lexer.state.inRawBlock;return{type:"text",raw:e[0],text:e[0],escaped:r}}}},ue=class Qr{constructor(e){O(this,"tokens");O(this,"options");O(this,"state");O(this,"inlineQueue");O(this,"tokenizer");this.tokens=[],this.tokens.links=Object.create(null),this.options=e||He,this.options.tokenizer=this.options.tokenizer||new nr,this.tokenizer=this.options.tokenizer,this.tokenizer.options=this.options,this.tokenizer.lexer=this,this.inlineQueue=[],this.state={inLink:!1,inRawBlock:!1,top:!0};let r={other:K,block:Gt.normal,inline:mt.normal};this.options.pedantic?(r.block=Gt.pedantic,r.inline=mt.pedantic):this.options.gfm&&(r.block=Gt.gfm,this.options.breaks?r.inline=mt.breaks:r.inline=mt.gfm),this.tokenizer.rules=r}static get rules(){return{block:Gt,inline:mt}}static lex(e,r){return new Qr(r).lex(e)}static lexInline(e,r){return new Qr(r).inlineTokens(e)}lex(e){e=e.replace(K.carriageReturn,`
`),this.blockTokens(e,this.tokens);for(let r=0;r<this.inlineQueue.length;r++){let n=this.inlineQueue[r];this.inlineTokens(n.src,n.tokens)}return this.inlineQueue=[],this.tokens}blockTokens(e,r=[],n=!1){var i,o,c;this.tokenizer.lexer=this,this.options.pedantic&&(e=e.replace(K.tabCharGlobal,"    ").replace(K.spaceLine,""));let s=1/0;for(;e;){if(e.length<s)s=e.length;else{this.infiniteLoopError(e.charCodeAt(0));break}let l;if((o=(i=this.options.extensions)==null?void 0:i.block)!=null&&o.some(d=>(l=d.call({lexer:this},e,r))?(e=e.substring(l.raw.length),r.push(l),!0):!1))continue;if(l=this.tokenizer.space(e)){e=e.substring(l.raw.length);let d=r.at(-1);l.raw.length===1&&d!==void 0?d.raw+=`
`:r.push(l);continue}if(l=this.tokenizer.code(e)){e=e.substring(l.raw.length);let d=r.at(-1);(d==null?void 0:d.type)==="paragraph"||(d==null?void 0:d.type)==="text"?(d.raw+=(d.raw.endsWith(`
`)?"":`
`)+l.raw,d.text+=`
`+l.text,this.inlineQueue.at(-1).src=d.text):r.push(l);continue}if(l=this.tokenizer.fences(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.heading(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.hr(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.blockquote(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.list(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.html(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.def(e)){e=e.substring(l.raw.length);let d=r.at(-1);(d==null?void 0:d.type)==="paragraph"||(d==null?void 0:d.type)==="text"?(d.raw+=(d.raw.endsWith(`
`)?"":`
`)+l.raw,d.text+=`
`+l.raw,this.inlineQueue.at(-1).src=d.text):this.tokens.links[l.tag]||(this.tokens.links[l.tag]={href:l.href,title:l.title},r.push(l));continue}if(l=this.tokenizer.table(e)){e=e.substring(l.raw.length),r.push(l);continue}if(l=this.tokenizer.lheading(e)){e=e.substring(l.raw.length),r.push(l);continue}let p=e;if((c=this.options.extensions)!=null&&c.startBlock){let d=1/0,h=e.slice(1),m;this.options.extensions.startBlock.forEach(R=>{m=R.call({lexer:this},h),typeof m=="number"&&m>=0&&(d=Math.min(d,m))}),d<1/0&&d>=0&&(p=e.substring(0,d+1))}if(this.state.top&&(l=this.tokenizer.paragraph(p))){let d=r.at(-1);n&&(d==null?void 0:d.type)==="paragraph"?(d.raw+=(d.raw.endsWith(`
`)?"":`
`)+l.raw,d.text+=`
`+l.text,this.inlineQueue.pop(),this.inlineQueue.at(-1).src=d.text):r.push(l),n=p.length!==e.length,e=e.substring(l.raw.length);continue}if(l=this.tokenizer.text(e)){e=e.substring(l.raw.length);let d=r.at(-1);(d==null?void 0:d.type)==="text"?(d.raw+=(d.raw.endsWith(`
`)?"":`
`)+l.raw,d.text+=`
`+l.text,this.inlineQueue.pop(),this.inlineQueue.at(-1).src=d.text):r.push(l);continue}if(e){this.infiniteLoopError(e.charCodeAt(0));break}}return this.state.top=!0,r}inline(e,r=[]){return this.inlineQueue.push({src:e,tokens:r}),r}inlineTokens(e,r=[]){var p,d,h,m,R;this.tokenizer.lexer=this;let n=e,s=null;if(this.tokens.links){let g=Object.keys(this.tokens.links);if(g.length>0)for(;(s=this.tokenizer.rules.inline.reflinkSearch.exec(n))!==null;)g.includes(s[0].slice(s[0].lastIndexOf("[")+1,-1))&&(n=n.slice(0,s.index)+"["+"a".repeat(s[0].length-2)+"]"+n.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex))}for(;(s=this.tokenizer.rules.inline.anyPunctuation.exec(n))!==null;)n=n.slice(0,s.index)+"++"+n.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);let i;for(;(s=this.tokenizer.rules.inline.blockSkip.exec(n))!==null;)i=s[2]?s[2].length:0,n=n.slice(0,s.index+i)+"["+"a".repeat(s[0].length-i-2)+"]"+n.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);n=((d=(p=this.options.hooks)==null?void 0:p.emStrongMask)==null?void 0:d.call({lexer:this},n))??n;let o=!1,c="",l=1/0;for(;e;){if(e.length<l)l=e.length;else{this.infiniteLoopError(e.charCodeAt(0));break}o||(c=""),o=!1;let g;if((m=(h=this.options.extensions)==null?void 0:h.inline)!=null&&m.some(E=>(g=E.call({lexer:this},e,r))?(e=e.substring(g.raw.length),r.push(g),!0):!1))continue;if(g=this.tokenizer.escape(e)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.tag(e)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.link(e)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.reflink(e,this.tokens.links)){e=e.substring(g.raw.length);let E=r.at(-1);g.type==="text"&&(E==null?void 0:E.type)==="text"?(E.raw+=g.raw,E.text+=g.text):r.push(g);continue}if(g=this.tokenizer.emStrong(e,n,c)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.codespan(e)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.br(e)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.del(e,n,c)){e=e.substring(g.raw.length),r.push(g);continue}if(g=this.tokenizer.autolink(e)){e=e.substring(g.raw.length),r.push(g);continue}if(!this.state.inLink&&(g=this.tokenizer.url(e))){e=e.substring(g.raw.length),r.push(g);continue}let Y=e;if((R=this.options.extensions)!=null&&R.startInline){let E=1/0,se=e.slice(1),ee;this.options.extensions.startInline.forEach(T=>{ee=T.call({lexer:this},se),typeof ee=="number"&&ee>=0&&(E=Math.min(E,ee))}),E<1/0&&E>=0&&(Y=e.substring(0,E+1))}if(g=this.tokenizer.inlineText(Y)){e=e.substring(g.raw.length),g.raw.slice(-1)!=="_"&&(c=g.raw.slice(-1)),o=!0;let E=r.at(-1);(E==null?void 0:E.type)==="text"?(E.raw+=g.raw,E.text+=g.text):r.push(g);continue}if(e){this.infiniteLoopError(e.charCodeAt(0));break}}return r}infiniteLoopError(e){let r="Infinite loop on byte: "+e;if(this.options.silent)console.error(r);else throw new Error(r)}},ir=class{constructor(t){O(this,"options");O(this,"parser");this.options=t||He}space(t){return""}code({text:t,lang:e,escaped:r}){var i;let n=(i=(e||"").match(K.notSpaceStart))==null?void 0:i[0],s=t.replace(K.endingNewline,"")+`
`;return n?'<pre><code class="language-'+ge(n)+'">'+(r?s:ge(s,!0))+`</code></pre>
`:"<pre><code>"+(r?s:ge(s,!0))+`</code></pre>
`}blockquote({tokens:t}){return`<blockquote>
${this.parser.parse(t)}</blockquote>
`}html({text:t}){return t}def(t){return""}heading({tokens:t,depth:e}){return`<h${e}>${this.parser.parseInline(t)}</h${e}>
`}hr(t){return`<hr>
`}list(t){let e=t.ordered,r=t.start,n="";for(let o=0;o<t.items.length;o++){let c=t.items[o];n+=this.listitem(c)}let s=e?"ol":"ul",i=e&&r!==1?' start="'+r+'"':"";return"<"+s+i+`>
`+n+"</"+s+`>
`}listitem(t){return`<li>${this.parser.parse(t.tokens)}</li>
`}checkbox({checked:t}){return"<input "+(t?'checked="" ':"")+'disabled="" type="checkbox"> '}paragraph({tokens:t}){return`<p>${this.parser.parseInline(t)}</p>
`}table(t){let e="",r="";for(let s=0;s<t.header.length;s++)r+=this.tablecell(t.header[s]);e+=this.tablerow({text:r});let n="";for(let s=0;s<t.rows.length;s++){let i=t.rows[s];r="";for(let o=0;o<i.length;o++)r+=this.tablecell(i[o]);n+=this.tablerow({text:r})}return n&&(n=`<tbody>${n}</tbody>`),`<table>
<thead>
`+e+`</thead>
`+n+`</table>
`}tablerow({text:t}){return`<tr>
${t}</tr>
`}tablecell(t){let e=this.parser.parseInline(t.tokens),r=t.header?"th":"td";return(t.align?`<${r} align="${t.align}">`:`<${r}>`)+e+`</${r}>
`}strong({tokens:t}){return`<strong>${this.parser.parseInline(t)}</strong>`}em({tokens:t}){return`<em>${this.parser.parseInline(t)}</em>`}codespan({text:t}){return`<code>${ge(t,!0)}</code>`}br(t){return"<br>"}del({tokens:t}){return`<del>${this.parser.parseInline(t)}</del>`}link({href:t,title:e,tokens:r}){let n=this.parser.parseInline(r),s=fn(t);if(s===null)return n;t=s;let i='<a href="'+t+'"';return e&&(i+=' title="'+ge(e)+'"'),i+=">"+n+"</a>",i}image({href:t,title:e,text:r,tokens:n}){n&&(r=this.parser.parseInline(n,this.parser.textRenderer));let s=fn(t);if(s===null)return ge(r);t=s;let i=`<img src="${t}" alt="${ge(r)}"`;return e&&(i+=` title="${ge(e)}"`),i+=">",i}text(t){return"tokens"in t&&t.tokens?this.parser.parseInline(t.tokens):"escaped"in t&&t.escaped?t.text:ge(t.text)}},ws=class{strong({text:t}){return t}em({text:t}){return t}codespan({text:t}){return t}del({text:t}){return t}html({text:t}){return t}text({text:t}){return t}link({text:t}){return""+t}image({text:t}){return""+t}br(){return""}checkbox({raw:t}){return t}},de=class Jr{constructor(e){O(this,"options");O(this,"renderer");O(this,"textRenderer");this.options=e||He,this.options.renderer=this.options.renderer||new ir,this.renderer=this.options.renderer,this.renderer.options=this.options,this.renderer.parser=this,this.textRenderer=new ws}static parse(e,r){return new Jr(r).parse(e)}static parseInline(e,r){return new Jr(r).parseInline(e)}parse(e){var n,s;this.renderer.parser=this;let r="";for(let i=0;i<e.length;i++){let o=e[i];if((s=(n=this.options.extensions)==null?void 0:n.renderers)!=null&&s[o.type]){let l=o,p=this.options.extensions.renderers[l.type].call({parser:this},l);if(p!==!1||!["space","hr","heading","code","table","blockquote","list","html","def","paragraph","text"].includes(l.type)){r+=p||"";continue}}let c=o;switch(c.type){case"space":{r+=this.renderer.space(c);break}case"hr":{r+=this.renderer.hr(c);break}case"heading":{r+=this.renderer.heading(c);break}case"code":{r+=this.renderer.code(c);break}case"table":{r+=this.renderer.table(c);break}case"blockquote":{r+=this.renderer.blockquote(c);break}case"list":{r+=this.renderer.list(c);break}case"checkbox":{r+=this.renderer.checkbox(c);break}case"html":{r+=this.renderer.html(c);break}case"def":{r+=this.renderer.def(c);break}case"paragraph":{r+=this.renderer.paragraph(c);break}case"text":{r+=this.renderer.text(c);break}default:{let l='Token with "'+c.type+'" type was not found.';if(this.options.silent)return console.error(l),"";throw new Error(l)}}}return r}parseInline(e,r=this.renderer){var s,i;this.renderer.parser=this;let n="";for(let o=0;o<e.length;o++){let c=e[o];if((i=(s=this.options.extensions)==null?void 0:s.renderers)!=null&&i[c.type]){let p=this.options.extensions.renderers[c.type].call({parser:this},c);if(p!==!1||!["escape","html","link","image","strong","em","codespan","br","del","text"].includes(c.type)){n+=p||"";continue}}let l=c;switch(l.type){case"escape":{n+=r.text(l);break}case"html":{n+=r.html(l);break}case"link":{n+=r.link(l);break}case"image":{n+=r.image(l);break}case"checkbox":{n+=r.checkbox(l);break}case"strong":{n+=r.strong(l);break}case"em":{n+=r.em(l);break}case"codespan":{n+=r.codespan(l);break}case"br":{n+=r.br(l);break}case"del":{n+=r.del(l);break}case"text":{n+=r.text(l);break}default:{let p='Token with "'+l.type+'" type was not found.';if(this.options.silent)return console.error(p),"";throw new Error(p)}}}return n}},Vt,vt=(Vt=class{constructor(t){O(this,"options");O(this,"block");this.options=t||He}preprocess(t){return t}postprocess(t){return t}processAllTokens(t){return t}emStrongMask(t){return t}provideLexer(t=this.block){return t?ue.lex:ue.lexInline}provideParser(t=this.block){return t?de.parse:de.parseInline}},O(Vt,"passThroughHooks",new Set(["preprocess","postprocess","processAllTokens","emStrongMask"])),O(Vt,"passThroughHooksRespectAsync",new Set(["preprocess","postprocess","processAllTokens"])),Vt),Io=class{constructor(...t){O(this,"defaults",ps());O(this,"options",this.setOptions);O(this,"parse",this.parseMarkdown(!0));O(this,"parseInline",this.parseMarkdown(!1));O(this,"Parser",de);O(this,"Renderer",ir);O(this,"TextRenderer",ws);O(this,"Lexer",ue);O(this,"Tokenizer",nr);O(this,"Hooks",vt);this.use(...t)}walkTokens(t,e){var n,s;let r=[];for(let i of t)switch(r=r.concat(e.call(this,i)),i.type){case"table":{let o=i;for(let c of o.header)r=r.concat(this.walkTokens(c.tokens,e));for(let c of o.rows)for(let l of c)r=r.concat(this.walkTokens(l.tokens,e));break}case"list":{let o=i;r=r.concat(this.walkTokens(o.items,e));break}default:{let o=i;(s=(n=this.defaults.extensions)==null?void 0:n.childTokens)!=null&&s[o.type]?this.defaults.extensions.childTokens[o.type].forEach(c=>{let l=o[c].flat(1/0);r=r.concat(this.walkTokens(l,e))}):o.tokens&&(r=r.concat(this.walkTokens(o.tokens,e)))}}return r}use(...t){let e=this.defaults.extensions||{renderers:{},childTokens:{}};return t.forEach(r=>{let n={...r};if(n.async=this.defaults.async||n.async||!1,r.extensions&&(r.extensions.forEach(s=>{if(!s.name)throw new Error("extension name required");if("renderer"in s){let i=e.renderers[s.name];i?e.renderers[s.name]=function(...o){let c=s.renderer.apply(this,o);return c===!1&&(c=i.apply(this,o)),c}:e.renderers[s.name]=s.renderer}if("tokenizer"in s){if(!s.level||s.level!=="block"&&s.level!=="inline")throw new Error("extension level must be 'block' or 'inline'");let i=e[s.level];i?i.unshift(s.tokenizer):e[s.level]=[s.tokenizer],s.start&&(s.level==="block"?e.startBlock?e.startBlock.push(s.start):e.startBlock=[s.start]:s.level==="inline"&&(e.startInline?e.startInline.push(s.start):e.startInline=[s.start]))}"childTokens"in s&&s.childTokens&&(e.childTokens[s.name]=s.childTokens)}),n.extensions=e),r.renderer){let s=this.defaults.renderer||new ir(this.defaults);for(let i in r.renderer){if(!(i in s))throw new Error(`renderer '${i}' does not exist`);if(["options","parser"].includes(i))continue;let o=i,c=r.renderer[o],l=s[o];s[o]=(...p)=>{let d=c.apply(s,p);return d===!1&&(d=l.apply(s,p)),d||""}}n.renderer=s}if(r.tokenizer){let s=this.defaults.tokenizer||new nr(this.defaults);for(let i in r.tokenizer){if(!(i in s))throw new Error(`tokenizer '${i}' does not exist`);if(["options","rules","lexer"].includes(i))continue;let o=i,c=r.tokenizer[o],l=s[o];s[o]=(...p)=>{let d=c.apply(s,p);return d===!1&&(d=l.apply(s,p)),d}}n.tokenizer=s}if(r.hooks){let s=this.defaults.hooks||new vt;for(let i in r.hooks){if(!(i in s))throw new Error(`hook '${i}' does not exist`);if(["options","block"].includes(i))continue;let o=i,c=r.hooks[o],l=s[o];vt.passThroughHooks.has(i)?s[o]=p=>{if(this.defaults.async&&vt.passThroughHooksRespectAsync.has(i))return(async()=>{let h=await c.call(s,p);return l.call(s,h)})();let d=c.call(s,p);return l.call(s,d)}:s[o]=(...p)=>{if(this.defaults.async)return(async()=>{let h=await c.apply(s,p);return h===!1&&(h=await l.apply(s,p)),h})();let d=c.apply(s,p);return d===!1&&(d=l.apply(s,p)),d}}n.hooks=s}if(r.walkTokens){let s=this.defaults.walkTokens,i=r.walkTokens;n.walkTokens=function(o){let c=[];return c.push(i.call(this,o)),s&&(c=c.concat(s.call(this,o))),c}}this.defaults={...this.defaults,...n}}),this}setOptions(t){return this.defaults={...this.defaults,...t},this}lexer(t,e){return ue.lex(t,e??this.defaults)}parser(t,e){return de.parse(t,e??this.defaults)}parseMarkdown(t){return(e,r)=>{let n={...r},s={...this.defaults,...n},i=this.onError(!!s.silent,!!s.async);if(this.defaults.async===!0&&n.async===!1)return i(new Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));if(typeof e>"u"||e===null)return i(new Error("marked(): input parameter is undefined or null"));if(typeof e!="string")return i(new Error("marked(): input parameter is of type "+Object.prototype.toString.call(e)+", string expected"));if(s.hooks&&(s.hooks.options=s,s.hooks.block=t),s.async)return(async()=>{let o=s.hooks?await s.hooks.preprocess(e):e,c=await(s.hooks?await s.hooks.provideLexer(t):t?ue.lex:ue.lexInline)(o,s),l=s.hooks?await s.hooks.processAllTokens(c):c;s.walkTokens&&await Promise.all(this.walkTokens(l,s.walkTokens));let p=await(s.hooks?await s.hooks.provideParser(t):t?de.parse:de.parseInline)(l,s);return s.hooks?await s.hooks.postprocess(p):p})().catch(i);try{s.hooks&&(e=s.hooks.preprocess(e));let o=(s.hooks?s.hooks.provideLexer(t):t?ue.lex:ue.lexInline)(e,s);s.hooks&&(o=s.hooks.processAllTokens(o)),s.walkTokens&&this.walkTokens(o,s.walkTokens);let c=(s.hooks?s.hooks.provideParser(t):t?de.parse:de.parseInline)(o,s);return s.hooks&&(c=s.hooks.postprocess(c)),c}catch(o){return i(o)}}}onError(t,e){return r=>{if(r.message+=`
Please report this to https://github.com/markedjs/marked.`,t){let n="<p>An error occurred:</p><pre>"+ge(r.message+"",!0)+"</pre>";return e?Promise.resolve(n):n}if(e)return Promise.reject(r);throw r}}},Me=new Io;function C(t,e){return Me.parse(t,e)}C.options=C.setOptions=function(t){return Me.setOptions(t),C.defaults=Me.defaults,Gn(C.defaults),C};C.getDefaults=ps;C.defaults=He;C.use=function(...t){return Me.use(...t),C.defaults=Me.defaults,Gn(C.defaults),C};C.walkTokens=function(t,e){return Me.walkTokens(t,e)};C.parseInline=Me.parseInline;C.Parser=de;C.parser=de.parse;C.Renderer=ir;C.TextRenderer=ws;C.Lexer=ue;C.lexer=ue.lex;C.Tokenizer=nr;C.Hooks=vt;C.parse=C;C.options;C.setOptions;C.use;C.walkTokens;C.parseInline;de.parse;ue.lex;/*! @license DOMPurify 3.4.9 | (c) Cure53 and other contributors | Released under the Apache license 2.0 and Mozilla Public License 2.0 | github.com/cure53/DOMPurify/blob/3.4.9/LICENSE */function vn(t,e){(e==null||e>t.length)&&(e=t.length);for(var r=0,n=Array(e);r<e;r++)n[r]=t[r];return n}function Lo(t){if(Array.isArray(t))return t}function Mo(t,e){var r=t==null?null:typeof Symbol<"u"&&t[Symbol.iterator]||t["@@iterator"];if(r!=null){var n,s,i,o,c=[],l=!0,p=!1;try{if(i=(r=r.call(t)).next,e!==0)for(;!(l=(n=i.call(r)).done)&&(c.push(n.value),c.length!==e);l=!0);}catch(d){p=!0,s=d}finally{try{if(!l&&r.return!=null&&(o=r.return(),Object(o)!==o))return}finally{if(p)throw s}}return c}}function zo(){throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Uo(t,e){return Lo(t)||Mo(t,e)||Ho(t,e)||zo()}function Ho(t,e){if(t){if(typeof t=="string")return vn(t,e);var r={}.toString.call(t).slice(8,-1);return r==="Object"&&t.constructor&&(r=t.constructor.name),r==="Map"||r==="Set"?Array.from(t):r==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(r)?vn(t,e):void 0}}const ri=Object.entries,yn=Object.setPrototypeOf,Fo=Object.isFrozen,Bo=Object.getPrototypeOf,jo=Object.getOwnPropertyDescriptor;let J=Object.freeze,ie=Object.seal,Xe=Object.create,si=typeof Reflect<"u"&&Reflect,es=si.apply,ts=si.construct;J||(J=function(e){return e});ie||(ie=function(e){return e});es||(es=function(e,r){for(var n=arguments.length,s=new Array(n>2?n-2:0),i=2;i<n;i++)s[i-2]=arguments[i];return e.apply(r,s)});ts||(ts=function(e){for(var r=arguments.length,n=new Array(r>1?r-1:0),s=1;s<r;s++)n[s-1]=arguments[s];return new e(...n)});const ve=F(Array.prototype.forEach),Wo=F(Array.prototype.lastIndexOf),wn=F(Array.prototype.pop),Ve=F(Array.prototype.push),qo=F(Array.prototype.splice),Q=Array.isArray,yt=F(String.prototype.toLowerCase),Ur=F(String.prototype.toString),xn=F(String.prototype.match),Ze=F(String.prototype.replace),kn=F(String.prototype.indexOf),Go=F(String.prototype.trim),Yo=F(Number.prototype.toString),Vo=F(Boolean.prototype.toString),_n=typeof BigInt>"u"?null:F(BigInt.prototype.toString),$n=typeof Symbol>"u"?null:F(Symbol.prototype.toString),N=F(Object.prototype.hasOwnProperty),bt=F(Object.prototype.toString),G=F(RegExp.prototype.test),Oe=Zo(TypeError);function F(t){return function(e){e instanceof RegExp&&(e.lastIndex=0);for(var r=arguments.length,n=new Array(r>1?r-1:0),s=1;s<r;s++)n[s-1]=arguments[s];return es(t,e,n)}}function Zo(t){return function(){for(var e=arguments.length,r=new Array(e),n=0;n<e;n++)r[n]=arguments[n];return ts(t,r)}}function k(t,e){let r=arguments.length>2&&arguments[2]!==void 0?arguments[2]:yt;if(yn&&yn(t,null),!Q(e))return t;let n=e.length;for(;n--;){let s=e[n];if(typeof s=="string"){const i=r(s);i!==s&&(Fo(e)||(e[n]=i),s=i)}t[s]=!0}return t}function Ko(t){for(let e=0;e<t.length;e++)N(t,e)||(t[e]=null);return t}function V(t){const e=Xe(null);for(const n of ri(t)){var r=Uo(n,2);const s=r[0],i=r[1];N(t,s)&&(Q(i)?e[s]=Ko(i):i&&typeof i=="object"&&i.constructor===Object?e[s]=V(i):e[s]=i)}return e}function Xo(t){switch(typeof t){case"string":return t;case"number":return Yo(t);case"boolean":return Vo(t);case"bigint":return _n?_n(t):"0";case"symbol":return $n?$n(t):"Symbol()";case"undefined":return bt(t);case"function":case"object":{if(t===null)return bt(t);const e=t,r=me(e,"toString");if(typeof r=="function"){const n=r(e);return typeof n=="string"?n:bt(n)}return bt(t)}default:return bt(t)}}function me(t,e){for(;t!==null;){const n=jo(t,e);if(n){if(n.get)return F(n.get);if(typeof n.value=="function")return F(n.value)}t=Bo(t)}function r(){return null}return r}function Qo(t){try{return G(t,""),!0}catch{return!1}}const Tn=J(["a","abbr","acronym","address","area","article","aside","audio","b","bdi","bdo","big","blink","blockquote","body","br","button","canvas","caption","center","cite","code","col","colgroup","content","data","datalist","dd","decorator","del","details","dfn","dialog","dir","div","dl","dt","element","em","fieldset","figcaption","figure","font","footer","form","h1","h2","h3","h4","h5","h6","head","header","hgroup","hr","html","i","img","input","ins","kbd","label","legend","li","main","map","mark","marquee","menu","menuitem","meter","nav","nobr","ol","optgroup","option","output","p","picture","pre","progress","q","rp","rt","ruby","s","samp","search","section","select","shadow","slot","small","source","spacer","span","strike","strong","style","sub","summary","sup","table","tbody","td","template","textarea","tfoot","th","thead","time","tr","track","tt","u","ul","var","video","wbr"]),Hr=J(["svg","a","altglyph","altglyphdef","altglyphitem","animatecolor","animatemotion","animatetransform","circle","clippath","defs","desc","ellipse","enterkeyhint","exportparts","filter","font","g","glyph","glyphref","hkern","image","inputmode","line","lineargradient","marker","mask","metadata","mpath","part","path","pattern","polygon","polyline","radialgradient","rect","stop","style","switch","symbol","text","textpath","title","tref","tspan","view","vkern"]),Fr=J(["feBlend","feColorMatrix","feComponentTransfer","feComposite","feConvolveMatrix","feDiffuseLighting","feDisplacementMap","feDistantLight","feDropShadow","feFlood","feFuncA","feFuncB","feFuncG","feFuncR","feGaussianBlur","feImage","feMerge","feMergeNode","feMorphology","feOffset","fePointLight","feSpecularLighting","feSpotLight","feTile","feTurbulence"]),Jo=J(["animate","color-profile","cursor","discard","font-face","font-face-format","font-face-name","font-face-src","font-face-uri","foreignobject","hatch","hatchpath","mesh","meshgradient","meshpatch","meshrow","missing-glyph","script","set","solidcolor","unknown","use"]),Br=J(["math","menclose","merror","mfenced","mfrac","mglyph","mi","mlabeledtr","mmultiscripts","mn","mo","mover","mpadded","mphantom","mroot","mrow","ms","mspace","msqrt","mstyle","msub","msup","msubsup","mtable","mtd","mtext","mtr","munder","munderover","mprescripts"]),el=J(["maction","maligngroup","malignmark","mlongdiv","mscarries","mscarry","msgroup","mstack","msline","msrow","semantics","annotation","annotation-xml","mprescripts","none"]),Sn=J(["#text"]),An=J(["accept","action","align","alt","autocapitalize","autocomplete","autopictureinpicture","autoplay","background","bgcolor","border","capture","cellpadding","cellspacing","checked","cite","class","clear","color","cols","colspan","command","commandfor","controls","controlslist","coords","crossorigin","datetime","decoding","default","dir","disabled","disablepictureinpicture","disableremoteplayback","download","draggable","enctype","enterkeyhint","exportparts","face","for","headers","height","hidden","high","href","hreflang","id","inert","inputmode","integrity","ismap","kind","label","lang","list","loading","loop","low","max","maxlength","media","method","min","minlength","multiple","muted","name","nonce","noshade","novalidate","nowrap","open","optimum","part","pattern","placeholder","playsinline","popover","popovertarget","popovertargetaction","poster","preload","pubdate","radiogroup","readonly","rel","required","rev","reversed","role","rows","rowspan","spellcheck","scope","selected","shape","size","sizes","slot","span","srclang","start","src","srcset","step","style","summary","tabindex","title","translate","type","usemap","valign","value","width","wrap","xmlns"]),jr=J(["accent-height","accumulate","additive","alignment-baseline","amplitude","ascent","attributename","attributetype","azimuth","basefrequency","baseline-shift","begin","bias","by","class","clip","clippathunits","clip-path","clip-rule","color","color-interpolation","color-interpolation-filters","color-profile","color-rendering","cx","cy","d","dx","dy","diffuseconstant","direction","display","divisor","dur","edgemode","elevation","end","exponent","fill","fill-opacity","fill-rule","filter","filterunits","flood-color","flood-opacity","font-family","font-size","font-size-adjust","font-stretch","font-style","font-variant","font-weight","fx","fy","g1","g2","glyph-name","glyphref","gradientunits","gradienttransform","height","href","id","image-rendering","in","in2","intercept","k","k1","k2","k3","k4","kerning","keypoints","keysplines","keytimes","lang","lengthadjust","letter-spacing","kernelmatrix","kernelunitlength","lighting-color","local","marker-end","marker-mid","marker-start","markerheight","markerunits","markerwidth","maskcontentunits","maskunits","max","mask","mask-type","media","method","mode","min","name","numoctaves","offset","operator","opacity","order","orient","orientation","origin","overflow","paint-order","path","pathlength","patterncontentunits","patterntransform","patternunits","points","preservealpha","preserveaspectratio","primitiveunits","r","rx","ry","radius","refx","refy","repeatcount","repeatdur","restart","result","rotate","scale","seed","shape-rendering","slope","specularconstant","specularexponent","spreadmethod","startoffset","stddeviation","stitchtiles","stop-color","stop-opacity","stroke-dasharray","stroke-dashoffset","stroke-linecap","stroke-linejoin","stroke-miterlimit","stroke-opacity","stroke","stroke-width","style","surfacescale","systemlanguage","tabindex","tablevalues","targetx","targety","transform","transform-origin","text-anchor","text-decoration","text-rendering","textlength","type","u1","u2","unicode","values","viewbox","visibility","version","vert-adv-y","vert-origin-x","vert-origin-y","width","word-spacing","wrap","writing-mode","xchannelselector","ychannelselector","x","x1","x2","xmlns","y","y1","y2","z","zoomandpan"]),En=J(["accent","accentunder","align","bevelled","close","columnalign","columnlines","columnspacing","columnspan","denomalign","depth","dir","display","displaystyle","encoding","fence","frame","height","href","id","largeop","length","linethickness","lquote","lspace","mathbackground","mathcolor","mathsize","mathvariant","maxsize","minsize","movablelimits","notation","numalign","open","rowalign","rowlines","rowspacing","rowspan","rspace","rquote","scriptlevel","scriptminsize","scriptsizemultiplier","selection","separator","separators","stretchy","subscriptshift","supscriptshift","symmetric","voffset","width","xmlns"]),Yt=J(["xlink:href","xml:id","xlink:title","xml:space","xmlns:xlink"]),tl=ie(/{{[\w\W]*|^[\w\W]*}}/g),rl=ie(/<%[\w\W]*|^[\w\W]*%>/g),sl=ie(/\${[\w\W]*/g),nl=ie(/^data-[\-\w.\u00B7-\uFFFF]+$/),il=ie(/^aria-[\-\w]+$/),Rn=ie(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i),al=ie(/^(?:\w+script|data):/i),ol=ie(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g),ll=ie(/^html$/i),cl=ie(/^[a-z][.\w]*(-[.\w]+)+$/i),fe={element:1,attribute:2,text:3,cdataSection:4,entityReference:5,entityNode:6,progressingInstruction:7,comment:8,document:9,documentType:10,documentFragment:11,notation:12},ul=function(){return typeof window>"u"?null:window},dl=function(e,r){if(typeof e!="object"||typeof e.createPolicy!="function")return null;let n=null;const s="data-tt-policy-suffix";r&&r.hasAttribute(s)&&(n=r.getAttribute(s));const i="dompurify"+(n?"#"+n:"");try{return e.createPolicy(i,{createHTML(o){return o},createScriptURL(o){return o}})}catch{return console.warn("TrustedTypes policy "+i+" could not be created."),null}},Cn=function(){return{afterSanitizeAttributes:[],afterSanitizeElements:[],afterSanitizeShadowDOM:[],beforeSanitizeAttributes:[],beforeSanitizeElements:[],beforeSanitizeShadowDOM:[],uponSanitizeAttribute:[],uponSanitizeElement:[],uponSanitizeShadowNode:[]}};function ni(){let t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:ul();const e=b=>ni(b);if(e.version="3.4.9",e.removed=[],!t||!t.document||t.document.nodeType!==fe.document||!t.Element)return e.isSupported=!1,e;let r=t.document;const n=r,s=n.currentScript;t.DocumentFragment;const i=t.HTMLTemplateElement,o=t.Node,c=t.Element,l=t.NodeFilter,p=t.NamedNodeMap;p===void 0&&(t.NamedNodeMap||t.MozNamedAttrMap),t.HTMLFormElement;const d=t.DOMParser,h=t.trustedTypes,m=c.prototype,R=me(m,"cloneNode"),g=me(m,"remove"),Y=me(m,"nextSibling"),E=me(m,"childNodes"),se=me(m,"parentNode"),ee=me(m,"shadowRoot"),T=me(m,"attributes"),x=o&&o.prototype?me(o.prototype,"nodeType"):null,v=o&&o.prototype?me(o.prototype,"nodeName"):null;if(typeof i=="function"){const b=r.createElement("template");b.content&&b.content.ownerDocument&&(r=b.content.ownerDocument)}let S,ne="",lt,ct=!1,ut=0;const _s=function(){if(ut>0)throw Oe('A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the "DOMPurify and Trusted Types" section of the README.')},Fe=function(a){_s(),ut++;try{return S.createHTML(a)}finally{ut--}},ai=function(a){_s(),ut++;try{return S.createScriptURL(a)}finally{ut--}},oi=function(){return ct||(lt=dl(h,s),ct=!0),lt},Dt=r,fr=Dt.implementation,$s=Dt.createNodeIterator,li=Dt.createDocumentFragment,ci=Dt.getElementsByTagName,ui=n.importNode;let j=Cn();e.isSupported=typeof ri=="function"&&typeof se=="function"&&fr&&fr.createHTMLDocument!==void 0;const Nt=tl,It=rl,Lt=sl,di=nl,pi=il,hi=al,Ts=ol,fi=cl;let Ss=Rn,I=null;const gr=k({},[...Tn,...Hr,...Fr,...Br,...Sn]);let L=null;const mr=k({},[...An,...jr,...En,...Yt]);let M=Object.seal(Xe(null,{tagNameCheck:{writable:!0,configurable:!1,enumerable:!0,value:null},attributeNameCheck:{writable:!0,configurable:!1,enumerable:!0,value:null},allowCustomizedBuiltInElements:{writable:!0,configurable:!1,enumerable:!0,value:!1}})),dt=null,Mt=null;const we=Object.seal(Xe(null,{tagCheck:{writable:!0,configurable:!1,enumerable:!0,value:null},attributeCheck:{writable:!0,configurable:!1,enumerable:!0,value:null}}));let As=!0,br=!0,Es=!1,Rs=!0,xe=!1,pt=!0,Ee=!1,vr=!1,yr=!1,Be=!1,zt=!1,Ut=!1,Cs=!0,Os=!1;const Ps="user-content-";let wr=!0,xr=!1,je={},pe=null;const kr=k({},["annotation-xml","audio","colgroup","desc","foreignobject","head","iframe","math","mi","mn","mo","ms","mtext","noembed","noframes","noscript","plaintext","script","selectedcontent","style","svg","template","thead","title","video","xmp"]);let Ds=null;const Ns=k({},["audio","video","img","source","image","track"]);let _r=null;const Is=k({},["alt","class","for","id","label","name","pattern","placeholder","role","summary","title","value","style","xmlns"]),Ht="http://www.w3.org/1998/Math/MathML",Ft="http://www.w3.org/2000/svg",he="http://www.w3.org/1999/xhtml";let We=he,$r=!1,Tr=null;const gi=k({},[Ht,Ft,he],Ur);let Sr=k({},["mi","mo","mn","ms","mtext"]),Ar=k({},["annotation-xml"]);const mi=k({},["title","style","font","a","script"]);let ht=null;const bi=["application/xhtml+xml","text/html"],vi="text/html";let D=null,qe=null;const yi=r.createElement("form"),Ls=function(a){return a instanceof RegExp||a instanceof Function},Er=function(){let a=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{};if(qe&&qe===a)return;(!a||typeof a!="object")&&(a={}),a=V(a),ht=bi.indexOf(a.PARSER_MEDIA_TYPE)===-1?vi:a.PARSER_MEDIA_TYPE,D=ht==="application/xhtml+xml"?Ur:yt,I=N(a,"ALLOWED_TAGS")&&Q(a.ALLOWED_TAGS)?k({},a.ALLOWED_TAGS,D):gr,L=N(a,"ALLOWED_ATTR")&&Q(a.ALLOWED_ATTR)?k({},a.ALLOWED_ATTR,D):mr,Tr=N(a,"ALLOWED_NAMESPACES")&&Q(a.ALLOWED_NAMESPACES)?k({},a.ALLOWED_NAMESPACES,Ur):gi,_r=N(a,"ADD_URI_SAFE_ATTR")&&Q(a.ADD_URI_SAFE_ATTR)?k(V(Is),a.ADD_URI_SAFE_ATTR,D):Is,Ds=N(a,"ADD_DATA_URI_TAGS")&&Q(a.ADD_DATA_URI_TAGS)?k(V(Ns),a.ADD_DATA_URI_TAGS,D):Ns,pe=N(a,"FORBID_CONTENTS")&&Q(a.FORBID_CONTENTS)?k({},a.FORBID_CONTENTS,D):kr,dt=N(a,"FORBID_TAGS")&&Q(a.FORBID_TAGS)?k({},a.FORBID_TAGS,D):V({}),Mt=N(a,"FORBID_ATTR")&&Q(a.FORBID_ATTR)?k({},a.FORBID_ATTR,D):V({}),je=N(a,"USE_PROFILES")?a.USE_PROFILES&&typeof a.USE_PROFILES=="object"?V(a.USE_PROFILES):a.USE_PROFILES:!1,As=a.ALLOW_ARIA_ATTR!==!1,br=a.ALLOW_DATA_ATTR!==!1,Es=a.ALLOW_UNKNOWN_PROTOCOLS||!1,Rs=a.ALLOW_SELF_CLOSE_IN_ATTR!==!1,xe=a.SAFE_FOR_TEMPLATES||!1,pt=a.SAFE_FOR_XML!==!1,Ee=a.WHOLE_DOCUMENT||!1,Be=a.RETURN_DOM||!1,zt=a.RETURN_DOM_FRAGMENT||!1,Ut=a.RETURN_TRUSTED_TYPE||!1,yr=a.FORCE_BODY||!1,Cs=a.SANITIZE_DOM!==!1,Os=a.SANITIZE_NAMED_PROPS||!1,wr=a.KEEP_CONTENT!==!1,xr=a.IN_PLACE||!1,Ss=Qo(a.ALLOWED_URI_REGEXP)?a.ALLOWED_URI_REGEXP:Rn,We=typeof a.NAMESPACE=="string"?a.NAMESPACE:he,Sr=N(a,"MATHML_TEXT_INTEGRATION_POINTS")&&a.MATHML_TEXT_INTEGRATION_POINTS&&typeof a.MATHML_TEXT_INTEGRATION_POINTS=="object"?V(a.MATHML_TEXT_INTEGRATION_POINTS):k({},["mi","mo","mn","ms","mtext"]),Ar=N(a,"HTML_INTEGRATION_POINTS")&&a.HTML_INTEGRATION_POINTS&&typeof a.HTML_INTEGRATION_POINTS=="object"?V(a.HTML_INTEGRATION_POINTS):k({},["annotation-xml"]);const u=N(a,"CUSTOM_ELEMENT_HANDLING")&&a.CUSTOM_ELEMENT_HANDLING&&typeof a.CUSTOM_ELEMENT_HANDLING=="object"?V(a.CUSTOM_ELEMENT_HANDLING):Xe(null);if(M=Xe(null),N(u,"tagNameCheck")&&Ls(u.tagNameCheck)&&(M.tagNameCheck=u.tagNameCheck),N(u,"attributeNameCheck")&&Ls(u.attributeNameCheck)&&(M.attributeNameCheck=u.attributeNameCheck),N(u,"allowCustomizedBuiltInElements")&&typeof u.allowCustomizedBuiltInElements=="boolean"&&(M.allowCustomizedBuiltInElements=u.allowCustomizedBuiltInElements),xe&&(br=!1),zt&&(Be=!0),je&&(I=k({},Sn),L=Xe(null),je.html===!0&&(k(I,Tn),k(L,An)),je.svg===!0&&(k(I,Hr),k(L,jr),k(L,Yt)),je.svgFilters===!0&&(k(I,Fr),k(L,jr),k(L,Yt)),je.mathMl===!0&&(k(I,Br),k(L,En),k(L,Yt))),we.tagCheck=null,we.attributeCheck=null,N(a,"ADD_TAGS")&&(typeof a.ADD_TAGS=="function"?we.tagCheck=a.ADD_TAGS:Q(a.ADD_TAGS)&&(I===gr&&(I=V(I)),k(I,a.ADD_TAGS,D))),N(a,"ADD_ATTR")&&(typeof a.ADD_ATTR=="function"?we.attributeCheck=a.ADD_ATTR:Q(a.ADD_ATTR)&&(L===mr&&(L=V(L)),k(L,a.ADD_ATTR,D))),N(a,"ADD_URI_SAFE_ATTR")&&Q(a.ADD_URI_SAFE_ATTR)&&k(_r,a.ADD_URI_SAFE_ATTR,D),N(a,"FORBID_CONTENTS")&&Q(a.FORBID_CONTENTS)&&(pe===kr&&(pe=V(pe)),k(pe,a.FORBID_CONTENTS,D)),N(a,"ADD_FORBID_CONTENTS")&&Q(a.ADD_FORBID_CONTENTS)&&(pe===kr&&(pe=V(pe)),k(pe,a.ADD_FORBID_CONTENTS,D)),wr&&(I["#text"]=!0),Ee&&k(I,["html","head","body"]),I.table&&(k(I,["tbody"]),delete dt.tbody),a.TRUSTED_TYPES_POLICY){if(typeof a.TRUSTED_TYPES_POLICY.createHTML!="function")throw Oe('TRUSTED_TYPES_POLICY configuration option must provide a "createHTML" hook.');if(typeof a.TRUSTED_TYPES_POLICY.createScriptURL!="function")throw Oe('TRUSTED_TYPES_POLICY configuration option must provide a "createScriptURL" hook.');const f=S;S=a.TRUSTED_TYPES_POLICY;try{ne=Fe("")}catch(y){throw S=f,y}}else a.TRUSTED_TYPES_POLICY===null?(S=void 0,ne=""):(S===void 0&&(S=oi()),S&&typeof ne=="string"&&(ne=Fe("")));(j.uponSanitizeElement.length>0||j.uponSanitizeAttribute.length>0)&&I===gr&&(I=V(I)),j.uponSanitizeAttribute.length>0&&L===mr&&(L=V(L)),J&&J(a),qe=a},Ms=k({},[...Hr,...Fr,...Jo]),zs=k({},[...Br,...el]),wi=function(a){let u=se(a);(!u||!u.tagName)&&(u={namespaceURI:We,tagName:"template"});const f=yt(a.tagName),y=yt(u.tagName);return Tr[a.namespaceURI]?a.namespaceURI===Ft?u.namespaceURI===he?f==="svg":u.namespaceURI===Ht?f==="svg"&&(y==="annotation-xml"||Sr[y]):!!Ms[f]:a.namespaceURI===Ht?u.namespaceURI===he?f==="math":u.namespaceURI===Ft?f==="math"&&Ar[y]:!!zs[f]:a.namespaceURI===he?u.namespaceURI===Ft&&!Ar[y]||u.namespaceURI===Ht&&!Sr[y]?!1:!zs[f]&&(mi[f]||!Ms[f]):!!(ht==="application/xhtml+xml"&&Tr[a.namespaceURI]):!1},ce=function(a){Ve(e.removed,{element:a});try{se(a).removeChild(a)}catch{if(g(a),!se(a))throw Oe("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place")}},Us=function(a){const u=E?E(a):a.childNodes;if(u){const y=[];ve(u,w=>{Ve(y,w)}),ve(y,w=>{try{g(w)}catch{}})}const f=T?T(a):null;if(f)for(let y=f.length-1;y>=0;--y){const w=f[y],$=w&&w.name;if(typeof $=="string")try{a.removeAttribute($)}catch{}}},Re=function(a,u){try{Ve(e.removed,{attribute:u.getAttributeNode(a),from:u})}catch{Ve(e.removed,{attribute:null,from:u})}if(u.removeAttribute(a),a==="is")if(Be||zt)try{ce(u)}catch{}else try{u.setAttribute(a,"")}catch{}},xi=function(a){const u=T?T(a):a.attributes;if(u)for(let f=u.length-1;f>=0;--f){const y=u[f],w=y&&y.name;if(!(typeof w!="string"||L[D(w)]))try{a.removeAttribute(w)}catch{}}},ki=function(a){const u=[a];for(;u.length>0;){const f=u.pop();(x?x(f):f.nodeType)===fe.element&&xi(f);const w=E?E(f):f.childNodes;if(w)for(let $=w.length-1;$>=0;--$)u.push(w[$])}},Hs=function(a){let u=null,f=null;if(yr)a="<remove></remove>"+a;else{const $=xn(a,/^[\r\n\t ]+/);f=$&&$[0]}ht==="application/xhtml+xml"&&We===he&&(a='<html xmlns="http://www.w3.org/1999/xhtml"><head></head><body>'+a+"</body></html>");const y=S?Fe(a):a;if(We===he)try{u=new d().parseFromString(y,ht)}catch{}if(!u||!u.documentElement){u=fr.createDocument(We,"template",null);try{u.documentElement.innerHTML=$r?ne:y}catch{}}const w=u.body||u.documentElement;return a&&f&&w.insertBefore(r.createTextNode(f),w.childNodes[0]||null),We===he?ci.call(u,Ee?"html":"body")[0]:Ee?u.documentElement:w},Fs=function(a){return $s.call(a.ownerDocument||a,a,l.SHOW_ELEMENT|l.SHOW_COMMENT|l.SHOW_TEXT|l.SHOW_PROCESSING_INSTRUCTION|l.SHOW_CDATA_SECTION,null)},Rr=function(a){var u,f;a.normalize();const y=$s.call(a.ownerDocument||a,a,l.SHOW_TEXT|l.SHOW_COMMENT|l.SHOW_CDATA_SECTION|l.SHOW_PROCESSING_INSTRUCTION,null);let w=y.nextNode();for(;w;){let B=w.data;ve([Nt,It,Lt],P=>{B=Ze(B,P," ")}),w.data=B,w=y.nextNode()}const $=(u=(f=a.querySelectorAll)===null||f===void 0?void 0:f.call(a,"template"))!==null&&u!==void 0?u:[];ve(Array.from($),B=>{Ge(B.content)&&Rr(B.content)})},Bt=function(a){const u=v?v(a):null;return typeof u!="string"||D(u)!=="form"?!1:typeof a.nodeName!="string"||typeof a.textContent!="string"||typeof a.removeChild!="function"||a.attributes!==T(a)||typeof a.removeAttribute!="function"||typeof a.setAttribute!="function"||typeof a.namespaceURI!="string"||typeof a.insertBefore!="function"||typeof a.hasChildNodes!="function"||a.nodeType!==x(a)||a.childNodes!==E(a)},Ge=function(a){if(!x||typeof a!="object"||a===null)return!1;try{return x(a)===fe.documentFragment}catch{return!1}},ft=function(a){if(!x||typeof a!="object"||a===null)return!1;try{return typeof x(a)=="number"}catch{return!1}};function be(b,a,u){ve(b,f=>{f.call(e,a,u,qe)})}const Bs=function(a){let u=null;if(be(j.beforeSanitizeElements,a,null),Bt(a))return ce(a),!0;const f=D(v?v(a):a.nodeName);if(be(j.uponSanitizeElement,a,{tagName:f,allowedTags:I}),pt&&a.hasChildNodes()&&!ft(a.firstElementChild)&&G(/<[/\w!]/g,a.innerHTML)&&G(/<[/\w!]/g,a.textContent)||pt&&a.namespaceURI===he&&f==="style"&&ft(a.firstElementChild)||a.nodeType===fe.progressingInstruction||pt&&a.nodeType===fe.comment&&G(/<[/\w]/g,a.data))return ce(a),!0;if(dt[f]||!(we.tagCheck instanceof Function&&we.tagCheck(f))&&!I[f]){if(!dt[f]&&Ws(f)&&(M.tagNameCheck instanceof RegExp&&G(M.tagNameCheck,f)||M.tagNameCheck instanceof Function&&M.tagNameCheck(f)))return!1;if(wr&&!pe[f]){const w=se(a),$=E(a);if($&&w){const B=$.length;for(let P=B-1;P>=0;--P){const z=xr?$[P]:R($[P],!0);w.insertBefore(z,Y(a))}}}return ce(a),!0}return(x?x(a):a.nodeType)===fe.element&&!wi(a)||(f==="noscript"||f==="noembed"||f==="noframes")&&G(/<\/no(script|embed|frames)/i,a.innerHTML)?(ce(a),!0):(xe&&a.nodeType===fe.text&&(u=a.textContent,ve([Nt,It,Lt],w=>{u=Ze(u,w," ")}),a.textContent!==u&&(Ve(e.removed,{element:a.cloneNode()}),a.textContent=u)),be(j.afterSanitizeElements,a,null),!1)},js=function(a,u,f){if(Mt[u]||Cs&&(u==="id"||u==="name")&&(f in r||f in yi))return!1;const y=L[u]||we.attributeCheck instanceof Function&&we.attributeCheck(u,a);if(!(br&&!Mt[u]&&G(di,u))){if(!(As&&G(pi,u))){if(!y||Mt[u]){if(!(Ws(a)&&(M.tagNameCheck instanceof RegExp&&G(M.tagNameCheck,a)||M.tagNameCheck instanceof Function&&M.tagNameCheck(a))&&(M.attributeNameCheck instanceof RegExp&&G(M.attributeNameCheck,u)||M.attributeNameCheck instanceof Function&&M.attributeNameCheck(u,a))||u==="is"&&M.allowCustomizedBuiltInElements&&(M.tagNameCheck instanceof RegExp&&G(M.tagNameCheck,f)||M.tagNameCheck instanceof Function&&M.tagNameCheck(f))))return!1}else if(!_r[u]){if(!G(Ss,Ze(f,Ts,""))){if(!((u==="src"||u==="xlink:href"||u==="href")&&a!=="script"&&kn(f,"data:")===0&&Ds[a])){if(!(Es&&!G(hi,Ze(f,Ts,"")))){if(f)return!1}}}}}}return!0},_i=k({},["annotation-xml","color-profile","font-face","font-face-format","font-face-name","font-face-src","font-face-uri","missing-glyph"]),Ws=function(a){return!_i[yt(a)]&&G(fi,a)},qs=function(a){be(j.beforeSanitizeAttributes,a,null);const u=a.attributes;if(!u||Bt(a))return;const f={attrName:"",attrValue:"",keepAttr:!0,allowedAttributes:L,forceKeepAttr:void 0};let y=u.length;for(;y--;){const w=u[y],$=w.name,B=w.namespaceURI,P=w.value,z=D($),ke=P;let W=$==="value"?ke:Go(ke);if(f.attrName=z,f.attrValue=W,f.keepAttr=!0,f.forceKeepAttr=void 0,be(j.uponSanitizeAttribute,a,f),W=f.attrValue,Os&&(z==="id"||z==="name")&&kn(W,Ps)!==0&&(Re($,a),W=Ps+W),pt&&G(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i,W)){Re($,a);continue}if(z==="attributename"&&xn(W,"href")){Re($,a);continue}if(f.forceKeepAttr)continue;if(!f.keepAttr){Re($,a);continue}if(!Rs&&G(/\/>/i,W)){Re($,a);continue}xe&&ve([Nt,It,Lt],Ys=>{W=Ze(W,Ys," ")});const Gs=D(a.nodeName);if(!js(Gs,z,W)){Re($,a);continue}if(S&&typeof h=="object"&&typeof h.getAttributeType=="function"&&!B)switch(h.getAttributeType(Gs,z)){case"TrustedHTML":{W=Fe(W);break}case"TrustedScriptURL":{W=ai(W);break}}if(W!==ke)try{B?a.setAttributeNS(B,$,W):a.setAttribute($,W),Bt(a)?ce(a):wn(e.removed)}catch{Re($,a)}}be(j.afterSanitizeAttributes,a,null)},jt=function(a){let u=null;const f=Fs(a);for(be(j.beforeSanitizeShadowDOM,a,null);u=f.nextNode();)if(be(j.uponSanitizeShadowNode,u,null),Bs(u),qs(u),Ge(u.content)&&jt(u.content),(x?x(u):u.nodeType)===fe.element){const w=ee?ee(u):u.shadowRoot;Ge(w)&&(Cr(w),jt(w))}be(j.afterSanitizeShadowDOM,a,null)},Cr=function(a){const u=[{node:a,shadow:null}];for(;u.length>0;){const f=u.pop();if(f.shadow){jt(f.shadow);continue}const y=f.node,$=(x?x(y):y.nodeType)===fe.element,B=E?E(y):y.childNodes;if(B)for(let P=B.length-1;P>=0;--P)u.push({node:B[P],shadow:null});if($){const P=v?v(y):null;if(typeof P=="string"&&D(P)==="template"){const z=y.content;Ge(z)&&u.push({node:z,shadow:null})}}if($){const P=ee?ee(y):y.shadowRoot;Ge(P)&&u.push({node:null,shadow:P},{node:P,shadow:null})}}};return e.sanitize=function(b){let a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},u=null,f=null,y=null,w=null;if($r=!b,$r&&(b="<!-->"),typeof b!="string"&&!ft(b)&&(b=Xo(b),typeof b!="string"))throw Oe("dirty is not a string, aborting");if(!e.isSupported)return b;vr||Er(a),e.removed=[];const $=xr&&typeof b!="string"&&ft(b);if($){const z=v?v(b):b.nodeName;if(typeof z=="string"){const ke=D(z);if(!I[ke]||dt[ke])throw Oe("root node is forbidden and cannot be sanitized in-place")}if(Bt(b))throw Oe("root node is clobbered and cannot be sanitized in-place");try{Cr(b)}catch(ke){throw Us(b),ke}}else if(ft(b))u=Hs("<!---->"),f=u.ownerDocument.importNode(b,!0),f.nodeType===fe.element&&f.nodeName==="BODY"||f.nodeName==="HTML"?u=f:u.appendChild(f),Cr(f);else{if(!Be&&!xe&&!Ee&&b.indexOf("<")===-1)return S&&Ut?Fe(b):b;if(u=Hs(b),!u)return Be?null:Ut?ne:""}u&&yr&&ce(u.firstChild);const B=Fs($?b:u);try{for(;y=B.nextNode();)Bs(y),qs(y),Ge(y.content)&&jt(y.content)}catch(z){throw $&&Us(b),z}if($)return ve(e.removed,z=>{z.element&&ki(z.element)}),xe&&Rr(b),b;if(Be){if(xe&&Rr(u),zt)for(w=li.call(u.ownerDocument);u.firstChild;)w.appendChild(u.firstChild);else w=u;return(L.shadowroot||L.shadowrootmode)&&(w=ui.call(n,w,!0)),w}let P=Ee?u.outerHTML:u.innerHTML;return Ee&&I["!doctype"]&&u.ownerDocument&&u.ownerDocument.doctype&&u.ownerDocument.doctype.name&&G(ll,u.ownerDocument.doctype.name)&&(P="<!DOCTYPE "+u.ownerDocument.doctype.name+`>
`+P),xe&&ve([Nt,It,Lt],z=>{P=Ze(P,z," ")}),S&&Ut?Fe(P):P},e.setConfig=function(){let b=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{};Er(b),vr=!0},e.clearConfig=function(){qe=null,vr=!1,S=lt,ne=""},e.isValidAttribute=function(b,a,u){qe||Er({});const f=D(b),y=D(a);return js(f,y,u)},e.addHook=function(b,a){typeof a=="function"&&Ve(j[b],a)},e.removeHook=function(b,a){if(a!==void 0){const u=Wo(j[b],a);return u===-1?void 0:qo(j[b],u,1)[0]}return wn(j[b])},e.removeHooks=function(b){j[b]=[]},e.removeAllHooks=function(){j=Cn()},e}var pl=ni(),hl=Object.defineProperty,fl=Object.getOwnPropertyDescriptor,ii=(t,e,r,n)=>{for(var s=n>1?void 0:n?fl(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&hl(e,r,s),s};C.setOptions({breaks:!0,gfm:!0});function gl(t){return pl.sanitize(C.parse(t,{async:!1}))}let ar=class extends X{render(){const t=this.msg;if(t.role==="user")return _`
        <div class="bubble user">
          ${t.image?_`<img class="attached" src=${t.image} alt="attached" />`:""}${t.text}
        </div>
      `;const e=!t.streaming&&(t.model||t.latency)?_`<div class="badge">
            ${t.model??""}${t.latency?` · ${t.latency<1e3?`${t.latency}ms`:`${(t.latency/1e3).toFixed(1)}s`}`:""}
          </div>`:"";return _`
      <div class="bubble ai ${t.streaming?"streaming":""}">
        <div class="md">${Ya(gl(t.text))}</div>
        ${e}
      </div>
    `}};ar.styles=ae`
    :host { display: grid; }
    .bubble {
      padding: var(--ds-space-3) var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      border: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      line-height: var(--ds-leading-normal);
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
      overflow-wrap: anywhere;
    }
    .user {
      background: rgba(var(--ds-periwinkle-rgb), 0.10);
      border-color: var(--ds-border-accent);
      justify-self: end;
      max-width: 85%;
      white-space: pre-wrap;
    }
    .ai { background: var(--ds-surface-1); justify-self: start; max-width: 94%; }
    .ai.streaming .md::after {
      content: "▋"; color: var(--ds-accent); animation: blink 1s steps(1) infinite;
    }
    .md :first-child { margin-top: 0; }
    .md :last-child { margin-bottom: 0; }
    .md p { margin: var(--ds-space-2) 0; }
    .md code {
      font-family: var(--ds-font-mono); font-size: 0.85em;
      background: var(--ds-surface-2); padding: 1px 5px;
      border-radius: var(--ds-radius-xs); color: var(--ds-accent);
    }
    .md pre {
      background: var(--ds-charcoal-900); border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-sm); padding: var(--ds-space-3);
      overflow-x: auto;
    }
    .md pre code { background: none; padding: 0; color: var(--ds-text); }
    .md ul, .md ol { padding-left: var(--ds-space-5); margin: var(--ds-space-2) 0; }
    .md a { color: var(--ds-accent); }
    .md table { border-collapse: collapse; margin: var(--ds-space-2) 0; }
    .md th, .md td { border: 1px solid var(--ds-border); padding: var(--ds-space-1) var(--ds-space-3); }
    .md blockquote {
      margin: var(--ds-space-2) 0; padding-left: var(--ds-space-3);
      border-left: 2px solid var(--ds-border-accent); color: var(--ds-text-soft);
    }
    img.attached {
      display: block; max-width: 280px; max-height: 240px;
      border-radius: var(--ds-radius-sm); border: 1px solid var(--ds-border);
      margin-bottom: var(--ds-space-2);
    }
    .badge {
      margin-top: var(--ds-space-2);
      font-family: var(--ds-font-mono);
      font-size: 0.65rem;
      color: var(--ds-text-faint);
    }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @keyframes blink { 50% { opacity: 0; } }
    @media (prefers-reduced-motion: reduce) { .bubble { animation: none; } }
  `;ii([le({attribute:!1})],ar.prototype,"msg",2);ar=ii([oe("chat-message")],ar);var ml=Object.defineProperty,bl=Object.getOwnPropertyDescriptor,xs=(t,e,r,n)=>{for(var s=n>1?void 0:n?bl(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&ml(e,r,s),s};const vl={model:"◇",route:"⇢",symbolic:"∑",oracle:"⚛",thinking:"…",tool_call:"⚙",tool_result:"✓",final:"●"};function yl(t){switch(t.t){case"route":return`routed: ${t.reason??""} → ${t.model??""}`;case"symbolic":return`verified by ${t.engine??"sympy"} (${t.kind}): ${t.result}`;case"oracle":return`${t.domain} oracle: ${t.result??t.element??""}`;case"tool_call":return`tool: ${t.tool}`;case"tool_result":return`result from ${t.tool}: ${String(t.result??"").slice(0,80)}`;case"model":return`model: ${t.model??"?"} (loop ${t.loop??1})`;case"thinking":return String(t.text??"").slice(0,100);default:return t.t}}let At=class extends X{constructor(){super(...arguments),this.steps=[],this.open=!0}render(){return this.steps.length?_`
      <div class="trail">
        <header @click=${()=>this.open=!this.open}>
          <span>${this.open?"▾":"▸"}</span>
          <span>reasoning · ${this.steps.length} step${this.steps.length>1?"s":""}</span>
        </header>
        ${this.open?_`<ul>
              ${this.steps.map(t=>_`
                  <li class=${t.t==="symbolic"||t.t==="oracle"?"verify":""}>
                    <span class="ic">${vl[t.t]??"·"}</span>
                    <span>${yl(t)}</span>
                  </li>
                `)}
            </ul>`:""}
      </div>
    `:_``}};At.styles=ae`
    :host { display: block; }
    .trail {
      border: 1px solid var(--ds-border);
      border-left: 2px solid var(--ds-accent);
      border-radius: var(--ds-radius-md);
      background: var(--ds-glass-thin);
      -webkit-backdrop-filter: blur(var(--ds-blur-sm));
      backdrop-filter: blur(var(--ds-blur-sm));
      font-family: var(--ds-font-mono);
      font-size: var(--ds-text-xs);
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    header {
      display: flex; align-items: center; gap: var(--ds-space-2);
      padding: var(--ds-space-2) var(--ds-space-3);
      color: var(--ds-text-muted);
      cursor: pointer;
      user-select: none;
      letter-spacing: var(--ds-tracking-wide);
      text-transform: uppercase;
      font-size: 0.62rem;
    }
    header:hover { color: var(--ds-text-soft); }
    ul { list-style: none; margin: 0; padding: 0 var(--ds-space-3) var(--ds-space-2); display: grid; gap: 3px; }
    li { display: flex; gap: var(--ds-space-2); color: var(--ds-text-soft); }
    li .ic { color: var(--ds-accent); width: 14px; text-align: center; }
    li.verify { color: var(--ds-success); }
    li.verify .ic { color: var(--ds-success); }
    @keyframes rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  `;xs([le({attribute:!1})],At.prototype,"steps",2);xs([re()],At.prototype,"open",2);At=xs([oe("reasoning-trail")],At);var wl=Object.defineProperty,xl=Object.getOwnPropertyDescriptor,hr=(t,e,r,n)=>{for(var s=n>1?void 0:n?xl(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&wl(e,r,s),s};const On=1280;async function kl(t){return new Promise(e=>{const r=new Image;r.onload=()=>{let{width:n,height:s}=r;if(Math.max(n,s)>On){const o=On/Math.max(n,s);n=Math.round(n*o),s=Math.round(s*o)}const i=document.createElement("canvas");i.width=n,i.height=s,i.getContext("2d").drawImage(r,0,0,n,s);try{e(i.toDataURL("image/jpeg",.85))}catch{e(t)}},r.onerror=()=>e(t),r.src=t})}let rt=class extends X{constructor(){super(...arguments),this.image=null,this.dragging=!1,this.onPaste=t=>{var e;for(const r of((e=t.clipboardData)==null?void 0:e.items)??[])if(r.type.startsWith("image/")){const n=r.getAsFile();n&&this.stageImage(n);return}}}firstUpdated(){document.addEventListener("paste",this.onPaste)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("paste",this.onPaste)}async stageImage(t){const e=await new Promise(r=>{const n=new FileReader;n.onload=()=>r(n.result),n.readAsDataURL(t)});this.image=await kl(e)}async onDrop(t){var n,s;t.preventDefault(),this.dragging=!1;const e=(s=(n=t.dataTransfer)==null?void 0:n.files)==null?void 0:s[0];if(!e)return;if(e.type.startsWith("image/"))return void this.stageImage(e);Z(`Ingesting ${e.name}…`,"info");const r=await un(e);r.ok?Z(`Absorbed ${r.source} (${r.chunks} chunks)`,"success"):Z(`Ingest failed: ${r.error??"unknown"}`,"danger")}autoGrow(){this.ta.style.height="auto",this.ta.style.height=`${Math.min(this.ta.scrollHeight,180)}px`}fire(){const t=this.ta.value.trim();!t&&!this.image||(this.dispatchEvent(new CustomEvent("send",{detail:{text:t,image:this.image},bubbles:!0,composed:!0})),this.ta.value="",this.image=null,this.autoGrow())}onKey(t){t.key==="Enter"&&!t.shiftKey&&(t.preventDefault(),this.fire())}pickFile(t,e){const r=document.createElement("input");r.type="file",r.accept=t,r.onchange=()=>{var n;return((n=r.files)==null?void 0:n[0])&&e(r.files[0])},r.click()}render(){return _`
      ${this.image?_`<span class="chip">
            <img src=${this.image} alt="staged" />
            image attached · sent to vision
            <button @click=${()=>this.image=null} aria-label="Remove">✕</button>
          </span>`:""}
      <div
        class="wrap ${this.dragging?"dragging":""}"
        @dragover=${t=>{t.preventDefault(),this.dragging=!0}}
        @dragleave=${()=>this.dragging=!1}
        @drop=${this.onDrop}
      >
        <button class="icon-btn" title="Attach image (vision)"
          @click=${()=>this.pickFile("image/*",t=>void this.stageImage(t))}>🖼</button>
        <button class="icon-btn" title="Ingest document into memory"
          @click=${()=>this.pickFile(".pdf,.txt,.md,.py,.js,.ts,.json",async t=>{Z(`Ingesting ${t.name}…`,"info");const e=await un(t);e.ok?Z(`Absorbed ${e.source} (${e.chunks} chunks)`,"success"):Z(`Ingest failed: ${e.error??"unknown"}`,"danger")})}>📎</button>
        <textarea rows="1" placeholder="Message DEEP…"
          @input=${this.autoGrow} @keydown=${this.onKey}></textarea>
        <ds-button variant="primary" @click=${this.fire}>Send</ds-button>
      </div>
    `}};rt.styles=ae`
    :host { display: block; }
    .wrap {
      display: flex; gap: var(--ds-space-2); align-items: flex-end;
      padding: var(--ds-space-2);
      background: var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      transition: border-color var(--ds-dur-fast) var(--ds-ease-out);
    }
    .wrap:focus-within { border-color: var(--ds-border-accent); }
    .wrap.dragging { outline: 1.5px dashed var(--ds-accent); outline-offset: 2px; }
    textarea {
      flex: 1; resize: none; border: 0; background: none; outline: none;
      color: var(--ds-text); font-family: var(--ds-font-sans);
      font-size: var(--ds-text-sm); line-height: var(--ds-leading-normal);
      max-height: 180px; padding: var(--ds-space-2);
    }
    textarea::placeholder { color: var(--ds-text-faint); }
    .icon-btn {
      display: grid; place-items: center;
      width: 34px; height: 34px; flex: none;
      border: 0; border-radius: var(--ds-radius-sm);
      background: none; color: var(--ds-text-muted); cursor: pointer;
      transition: color var(--ds-dur-fast), background var(--ds-dur-fast);
    }
    .icon-btn:hover { color: var(--ds-accent); background: rgba(var(--ds-periwinkle-rgb), 0.1); }
    .chip {
      display: inline-flex; align-items: center; gap: var(--ds-space-2);
      margin-bottom: var(--ds-space-2);
      padding: var(--ds-space-1) var(--ds-space-2);
      background: var(--ds-glass);
      border: 1px solid var(--ds-border);
      border-left: 2px solid var(--ds-accent);
      border-radius: var(--ds-radius-sm);
      font-size: var(--ds-text-xs); color: var(--ds-text-soft);
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    .chip img { width: 26px; height: 26px; object-fit: cover; border-radius: var(--ds-radius-xs); }
    .chip button { border: 0; background: none; color: var(--ds-text-muted); cursor: pointer; }
    .chip button:hover { color: var(--ds-danger); }
    @keyframes rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  `;hr([re()],rt.prototype,"image",2);hr([re()],rt.prototype,"dragging",2);hr([os("textarea")],rt.prototype,"ta",2);rt=hr([oe("chat-composer")],rt);var _l=Object.getOwnPropertyDescriptor,$l=(t,e,r,n)=>{for(var s=n>1?void 0:n?_l(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=o(s)||s);return s};let rs=class extends jn(X){updated(){const t=this.renderRoot.querySelector(".scroll");t&&(t.scrollTop=t.scrollHeight)}render(){const t=te.get(),e=er.get();return _`
      <div class="scroll">
        ${t.length===0?_`<div class="empty">
              <h2>How can I help, Aryan?</h2>
              <p>Ask anything — drop an image for vision, or a document to absorb it.</p>
            </div>`:t.map(r=>_`<chat-message .msg=${r}></chat-message>`)}
        ${e.length&&(Te.get()||_a.get())?_`<reasoning-trail .steps=${e}></reasoning-trail>`:""}
        ${Te.get()?_`<div class="thinking"><span></span><span></span><span></span></div>`:""}
      </div>
      <div class="composer-area">
        <chat-composer
          @send=${r=>$a(r.detail.text,r.detail.image)}
        ></chat-composer>
      </div>
    `}};rs.styles=ae`
    :host {
      display: grid;
      grid-template-rows: 1fr auto;
      height: 100%;
      max-width: 820px;
      margin: 0 auto;
      width: 100%;
      padding: 0 var(--ds-space-4);
    }
    .scroll {
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: var(--ds-space-3);
      padding: var(--ds-space-5) var(--ds-space-1);
      scroll-behavior: smooth;
    }
    .empty {
      margin: auto;
      text-align: center;
      color: var(--ds-text-muted);
    }
    .empty h2 { color: var(--ds-text-soft); font-weight: 600; margin: 0 0 var(--ds-space-2); }
    .thinking {
      align-self: flex-start;
      display: inline-flex; gap: 5px;
      padding: var(--ds-space-3) var(--ds-space-4);
      background: var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-md);
    }
    .thinking span {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--ds-accent);
      animation: pulse 1.2s ease-in-out infinite;
    }
    .thinking span:nth-child(2) { animation-delay: 0.15s; }
    .thinking span:nth-child(3) { animation-delay: 0.3s; }
    .composer-area { padding: var(--ds-space-3) 0 var(--ds-space-5); }
    @keyframes pulse { 0%, 100% { opacity: 0.25; } 50% { opacity: 1; } }
  `;rs=$l([oe("deep-chat")],rs);var Tl=Object.defineProperty,Sl=Object.getOwnPropertyDescriptor,Ot=(t,e,r,n)=>{for(var s=n>1?void 0:n?Sl(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&Tl(e,r,s),s};function Al(t){const e=t.atomic_number;return e>=57&&e<=71?{row:9,col:3+(e-57)}:e>=89&&e<=103?{row:10,col:3+(e-89)}:t.group&&t.period?{row:t.period,col:t.group}:null}let ze=class extends X{constructor(){super(...arguments),this.elements=[],this.detail=null,this.constants=[],this.formulas=[]}connectedCallback(){super.connectedCallback(),Ca().then(t=>this.elements=t.elements).catch(()=>{}),Pa().then(t=>this.constants=t.constants).catch(()=>{}),Da().then(t=>this.formulas=t.formulas).catch(()=>{})}async pick(t){const e=await Oa(t).catch(()=>null);e!=null&&e.ok&&e.element&&(this.detail=e.element)}renderDetail(){const t=this.detail;if(!t)return _`<span style="color:var(--ds-text-muted)">Select an element for verified data.</span>`;const e=(r,n)=>n==null?"":_`<div class="row"><span>${r}</span><b>${n}</b></div>`;return _`
      <div class="detail">
        <span class="title">${t.name} (${t.symbol}) · Z=${t.atomic_number}</span>
        ${e("Atomic weight",t.atomic_weight)}
        ${e("Electron config",t.electron_configuration)}
        ${e("Electronegativity",t.electronegativity)}
        ${e("Oxidation states",Array.isArray(t.oxidation_states)?t.oxidation_states.join(", "):null)}
        ${e("Melting point (K)",t.melting_point_K)}
        ${e("Boiling point (K)",t.boiling_point_K)}
        ${e("Density (g/cm³)",t.density_g_cm3)}
        ${e("Category",t.series)}
        ${e("Discovered",t.discovery_year)}
      </div>
    `}render(){return _`
      <ds-panel heading="Periodic table · ${this.elements.length} elements · curated data">
        <div class="grid">
          ${this.elements.map(t=>{const e=Al(t);return e?_`
              <button class="cell cat-${t.category}" title=${t.name}
                style="grid-row:${e.row};grid-column:${e.col}"
                @click=${()=>void this.pick(t.atomic_number)}>
                <span class="z">${t.atomic_number}</span>
                <span class="sym">${t.symbol}</span>
              </button>
            `:""})}
        </div>
        <div style="margin-top:var(--ds-space-4)">${this.renderDetail()}</div>
      </ds-panel>

      <div class="cols">
        <ds-panel heading="Physical constants · CODATA">
          <div class="list mono">
            ${this.constants.map(t=>_`<div class="row"><span>${t.name} (${t.symbol})</span><b>${t.value} ${t.unit}</b></div>`)}
          </div>
        </ds-panel>
        <ds-panel heading="Formula library · ancient → modern">
          <div class="list mono">
            ${this.formulas.map(t=>_`<div class="row"><span>${t.name} <span class="era">${t.era}</span></span><b>${t.formula}</b></div>`)}
          </div>
        </ds-panel>
      </div>
    `}};ze.styles=ae`
    :host {
      display: grid;
      gap: var(--ds-space-5);
      padding: var(--ds-space-5);
      max-width: 1100px;
      margin: 0 auto;
    }
    .grid { display: grid; grid-template-columns: repeat(18, 1fr); gap: 3px; }
    button.cell {
      aspect-ratio: 1; min-width: 0; padding: 2px 3px;
      display: flex; flex-direction: column; align-items: flex-start; justify-content: space-between;
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-xs);
      background: var(--ds-surface-2);
      color: var(--ds-text); cursor: pointer; overflow: hidden;
      transition: transform var(--ds-dur-fast) var(--ds-ease-spring), box-shadow var(--ds-dur-fast) var(--ds-ease-out);
    }
    button.cell:hover { transform: scale(1.14); box-shadow: var(--ds-elev-3); z-index: 2; }
    .z { font-size: 0.5rem; opacity: 0.65; }
    .sym { font-size: 0.85rem; font-weight: 700; line-height: 1; }
    .cat-nonmetal { background: rgba(86,197,150,0.16); border-color: rgba(86,197,150,0.45); }
    .cat-noble { background: rgba(181,140,255,0.16); border-color: rgba(181,140,255,0.45); }
    .cat-alkali { background: rgba(229,115,106,0.16); border-color: rgba(229,115,106,0.45); }
    .cat-alkaline { background: rgba(224,163,90,0.16); border-color: rgba(224,163,90,0.45); }
    .cat-metalloid { background: rgba(94,200,229,0.16); border-color: rgba(94,200,229,0.45); }
    .cat-halogen { background: rgba(124,147,255,0.16); border-color: rgba(124,147,255,0.45); }
    .cat-transition { background: rgba(154,140,255,0.12); border-color: rgba(154,140,255,0.35); }
    .cat-lanthanide { background: rgba(94,200,229,0.10); border-color: rgba(94,200,229,0.3); }
    .cat-actinide { background: rgba(86,197,150,0.10); border-color: rgba(86,197,150,0.3); }
    .detail { font-size: var(--ds-text-sm); display: grid; gap: 4px; }
    .detail .title { font-size: var(--ds-text-lg); font-weight: 700; color: var(--ds-accent); }
    .row { display: flex; justify-content: space-between; gap: var(--ds-space-4); border-bottom: 1px solid var(--ds-border); padding: 2px 0; }
    .row span { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ds-space-5); }
    @media (max-width: 800px) { .cols { grid-template-columns: 1fr; } }
    .mono { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .list { display: grid; gap: 4px; max-height: 300px; overflow-y: auto; }
    .era { color: var(--ds-text-faint); text-transform: uppercase; font-size: 0.6rem; letter-spacing: var(--ds-tracking-wide); }
  `;Ot([re()],ze.prototype,"elements",2);Ot([re()],ze.prototype,"detail",2);Ot([re()],ze.prototype,"constants",2);Ot([re()],ze.prototype,"formulas",2);ze=Ot([oe("science-view")],ze);var El=Object.defineProperty,Rl=Object.getOwnPropertyDescriptor,Pt=(t,e,r,n)=>{for(var s=n>1?void 0:n?Rl(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&El(e,r,s),s};let Ue=class extends X{constructor(){super(...arguments),this.open=!1,this.q="",this.sel=0}show(){this.open=!0,this.q="",this.sel=0,requestAnimationFrame(()=>{var t;return(t=this.input)==null?void 0:t.focus()})}hide(){this.open=!1}toggle(){this.open?this.hide():this.show()}results(){return za(this.q)}run(t){this.hide(),t.run()}onKey(t){const e=this.results();t.key==="Escape"?this.hide():t.key==="ArrowDown"?(t.preventDefault(),this.sel=Math.min(this.sel+1,e.length-1)):t.key==="ArrowUp"?(t.preventDefault(),this.sel=Math.max(this.sel-1,0)):t.key==="Enter"&&e[this.sel]&&this.run(e[this.sel])}render(){if(!this.open)return _``;const t=this.results();return _`
      <div class="scrim" @click=${e=>{e.target===e.currentTarget&&this.hide()}}>
        <div class="box">
          <input
            placeholder="Type a command…"
            .value=${this.q}
            @input=${e=>{this.q=e.target.value,this.sel=0}}
            @keydown=${this.onKey}
          />
          ${t.length?_`<ul>
                ${t.map((e,r)=>_`
                    <li class=${r===this.sel?"sel":""}
                        @mouseenter=${()=>this.sel=r}
                        @click=${()=>this.run(e)}>
                      <span>${e.label}</span>
                      ${e.hint?_`<span class="hint">${e.hint}</span>`:""}
                    </li>
                  `)}
              </ul>`:_`<div class="none">No matching commands.</div>`}
        </div>
      </div>
    `}};Ue.styles=ae`
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
  `;Pt([re()],Ue.prototype,"open",2);Pt([re()],Ue.prototype,"q",2);Pt([re()],Ue.prototype,"sel",2);Pt([os("input")],Ue.prototype,"input",2);Ue=Pt([oe("command-palette")],Ue);var Cl=Object.defineProperty,Ol=Object.getOwnPropertyDescriptor,ks=(t,e,r,n)=>{for(var s=n>1?void 0:n?Ol(e,r):e,i=t.length-1,o;i>=0;i--)(o=t[i])&&(s=(n?o(e,r,s):o(s))||s);return n&&s&&Cl(e,r,s),s};let Et=class extends jn(X){constructor(){super(...arguments),this.route=location.hash.slice(1)||"home",this.status="—",this.onHash=()=>{this.route=location.hash.slice(1)||"home"},this.onGlobalKey=t=>{var e;(t.ctrlKey||t.metaKey)&&t.key.toLowerCase()==="k"&&(t.preventDefault(),(e=this.renderRoot.querySelector("command-palette"))==null||e.toggle())}}connectedCallback(){super.connectedCallback(),Aa(),Ea().then(t=>this.status=t.deep).catch(()=>this.status="offline"),window.addEventListener("hashchange",this.onHash),window.addEventListener("keydown",this.onGlobalKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("hashchange",this.onHash),window.removeEventListener("keydown",this.onGlobalKey)}render(){const t=Vr.get();return _`
      <header>
        <span class="dot ${t==="open"?"open":""}"></span>
        <span class="logo">DEEP</span>
        <span class="spacer"></span>
        <nav>
          <a href="#home">chat</a>
          <a href="#science">science</a>
          <a href="#gallery">gallery</a>
        </nav>
        <span class="meta">${this.status} · ${Wn.get()}</span>
        <span class="meta kbd" title="Command palette">⌘K</span>
      </header>
      <main>
        ${this.route==="gallery"?_`<ds-gallery></ds-gallery>`:this.route==="science"?_`<science-view></science-view>`:_`<deep-chat></deep-chat>`}
      </main>
      <command-palette></command-palette>
    `}};Et.styles=ae`
    :host { display: grid; grid-template-rows: auto 1fr; height: 100%; }
    header {
      display: flex; align-items: center; gap: var(--ds-space-3);
      padding: var(--ds-space-3) var(--ds-space-5);
      border-bottom: 1px solid var(--ds-border);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
    }
    .logo { font-weight: 700; letter-spacing: 0.02em; }
    .dot { width: 8px; height: 8px; border-radius: var(--ds-radius-pill); background: var(--ds-danger); }
    .dot.open { background: var(--ds-success); box-shadow: 0 0 8px var(--ds-success); }
    .spacer { flex: 1; }
    .meta { font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    nav a { color: var(--ds-text-muted); font-size: var(--ds-text-sm); text-decoration: none; margin-right: var(--ds-space-3); }
    nav a:hover { color: var(--ds-accent); }
    .kbd {
      padding: 2px 7px;
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-xs);
      font-size: 0.65rem;
      cursor: default;
    }

    main { overflow: auto; }
    .probe {
      max-width: 720px; margin: 0 auto; padding: var(--ds-space-5);
      display: grid; gap: var(--ds-space-3);
    }
    .msgs { display: grid; gap: var(--ds-space-2); }
    .msg {
      padding: var(--ds-space-3) var(--ds-space-4);
      border-radius: var(--ds-radius-md);
      border: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
      white-space: pre-wrap;
      animation: rise var(--ds-dur-base) var(--ds-ease-spring);
    }
    .user { background: rgba(var(--ds-periwinkle-rgb), 0.10); border-color: var(--ds-border-accent); justify-self: end; max-width: 85%; }
    .ai { background: var(--ds-surface-1); justify-self: start; max-width: 92%; }
    .ai.streaming::after { content: "▋"; color: var(--ds-accent); animation: blink 1s steps(1) infinite; }
    .row { display: flex; gap: var(--ds-space-2); align-items: end; }
    .row ds-field { flex: 1; }
    .hint { color: var(--ds-text-muted); font-size: var(--ds-text-xs); font-family: var(--ds-font-mono); }
    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @keyframes blink { 50% { opacity: 0; } }
  `;ks([re()],Et.prototype,"route",2);ks([re()],Et.prototype,"status",2);Et=ks([oe("deep-app")],Et);
//# sourceMappingURL=index-1D3ehaa5.js.map
