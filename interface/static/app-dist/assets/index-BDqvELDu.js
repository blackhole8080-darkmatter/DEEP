(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))o(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const n of i.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&o(n)}).observe(document,{childList:!0,subtree:!0});function s(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function o(r){if(r.ep)return;r.ep=!0;const i=s(r);fetch(r.href,i)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const oe=globalThis,ke=oe.ShadowRoot&&(oe.ShadyCSS===void 0||oe.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Ie=Symbol(),Le=new WeakMap;let st=class{constructor(e,s,o){if(this._$cssResult$=!0,o!==Ie)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=s}get styleSheet(){let e=this.o;const s=this.t;if(ke&&e===void 0){const o=s!==void 0&&s.length===1;o&&(e=Le.get(s)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),o&&Le.set(s,e))}return e}toString(){return this.cssText}};const bt=t=>new st(typeof t=="string"?t:t+"",void 0,Ie),z=(t,...e)=>{const s=t.length===1?t[0]:e.reduce((o,r,i)=>o+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+t[i+1],t[0]);return new st(s,t,Ie)},_t=(t,e)=>{if(ke)t.adoptedStyleSheets=e.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of e){const o=document.createElement("style"),r=oe.litNonce;r!==void 0&&o.setAttribute("nonce",r),o.textContent=s.cssText,t.appendChild(o)}},je=ke?t=>t:t=>t instanceof CSSStyleSheet?(e=>{let s="";for(const o of e.cssRules)s+=o.cssText;return bt(s)})(t):t;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:wt,defineProperty:xt,getOwnPropertyDescriptor:St,getOwnPropertyNames:At,getOwnPropertySymbols:Ct,getPrototypeOf:Et}=Object,E=globalThis,ze=E.trustedTypes,Ot=ze?ze.emptyScript:"",me=E.reactiveElementPolyfillSupport,G=(t,e)=>t,ne={toAttribute(t,e){switch(e){case Boolean:t=t?Ot:null;break;case Object:case Array:t=t==null?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=t!==null;break;case Number:s=t===null?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch{s=null}}return s}},De=(t,e)=>!wt(t,e),qe={attribute:!0,type:String,converter:ne,reflect:!1,useDefault:!1,hasChanged:De};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),E.litPropertyMetadata??(E.litPropertyMetadata=new WeakMap);let U=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??(this.l=[])).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,s=qe){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(e,s),!s.noAccessor){const o=Symbol(),r=this.getPropertyDescriptor(e,o,s);r!==void 0&&xt(this.prototype,e,r)}}static getPropertyDescriptor(e,s,o){const{get:r,set:i}=St(this.prototype,e)??{get(){return this[s]},set(n){this[s]=n}};return{get:r,set(n){const a=r==null?void 0:r.call(this);i==null||i.call(this,n),this.requestUpdate(e,a,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??qe}static _$Ei(){if(this.hasOwnProperty(G("elementProperties")))return;const e=Et(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(G("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(G("properties"))){const s=this.properties,o=[...At(s),...Ct(s)];for(const r of o)this.createProperty(r,s[r])}const e=this[Symbol.metadata];if(e!==null){const s=litPropertyMetadata.get(e);if(s!==void 0)for(const[o,r]of s)this.elementProperties.set(o,r)}this._$Eh=new Map;for(const[s,o]of this.elementProperties){const r=this._$Eu(s,o);r!==void 0&&this._$Eh.set(r,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const s=[];if(Array.isArray(e)){const o=new Set(e.flat(1/0).reverse());for(const r of o)s.unshift(je(r))}else e!==void 0&&s.push(je(e));return s}static _$Eu(e,s){const o=s.attribute;return o===!1?void 0:typeof o=="string"?o:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(s=>this.enableUpdating=s),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(s=>s(this))}addController(e){var s;(this._$EO??(this._$EO=new Set)).add(e),this.renderRoot!==void 0&&this.isConnected&&((s=e.hostConnected)==null||s.call(e))}removeController(e){var s;(s=this._$EO)==null||s.delete(e)}_$E_(){const e=new Map,s=this.constructor.elementProperties;for(const o of s.keys())this.hasOwnProperty(o)&&(e.set(o,this[o]),delete this[o]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return _t(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(s=>{var o;return(o=s.hostConnected)==null?void 0:o.call(s)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(s=>{var o;return(o=s.hostDisconnected)==null?void 0:o.call(s)})}attributeChangedCallback(e,s,o){this._$AK(e,o)}_$ET(e,s){var i;const o=this.constructor.elementProperties.get(e),r=this.constructor._$Eu(e,o);if(r!==void 0&&o.reflect===!0){const n=(((i=o.converter)==null?void 0:i.toAttribute)!==void 0?o.converter:ne).toAttribute(s,o.type);this._$Em=e,n==null?this.removeAttribute(r):this.setAttribute(r,n),this._$Em=null}}_$AK(e,s){var i,n;const o=this.constructor,r=o._$Eh.get(e);if(r!==void 0&&this._$Em!==r){const a=o.getPropertyOptions(r),d=typeof a.converter=="function"?{fromAttribute:a.converter}:((i=a.converter)==null?void 0:i.fromAttribute)!==void 0?a.converter:ne;this._$Em=r;const l=d.fromAttribute(s,a.type);this[r]=l??((n=this._$Ej)==null?void 0:n.get(r))??l,this._$Em=null}}requestUpdate(e,s,o,r=!1,i){var n;if(e!==void 0){const a=this.constructor;if(r===!1&&(i=this[e]),o??(o=a.getPropertyOptions(e)),!((o.hasChanged??De)(i,s)||o.useDefault&&o.reflect&&i===((n=this._$Ej)==null?void 0:n.get(e))&&!this.hasAttribute(a._$Eu(e,o))))return;this.C(e,s,o)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,s,{useDefault:o,reflect:r,wrapped:i},n){o&&!(this._$Ej??(this._$Ej=new Map)).has(e)&&(this._$Ej.set(e,n??s??this[e]),i!==!0||n!==void 0)||(this._$AL.has(e)||(this.hasUpdated||o||(s=void 0),this._$AL.set(e,s)),r===!0&&this._$Em!==e&&(this._$Eq??(this._$Eq=new Set)).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var o;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}const r=this.constructor.elementProperties;if(r.size>0)for(const[i,n]of r){const{wrapped:a}=n,d=this[i];a!==!0||this._$AL.has(i)||d===void 0||this.C(i,void 0,n,d)}}let e=!1;const s=this._$AL;try{e=this.shouldUpdate(s),e?(this.willUpdate(s),(o=this._$EO)==null||o.forEach(r=>{var i;return(i=r.hostUpdate)==null?void 0:i.call(r)}),this.update(s)):this._$EM()}catch(r){throw e=!1,this._$EM(),r}e&&this._$AE(s)}willUpdate(e){}_$AE(e){var s;(s=this._$EO)==null||s.forEach(o=>{var r;return(r=o.hostUpdated)==null?void 0:r.call(o)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(s=>this._$ET(s,this[s]))),this._$EM()}updated(e){}firstUpdated(e){}};U.elementStyles=[],U.shadowRootOptions={mode:"open"},U[G("elementProperties")]=new Map,U[G("finalized")]=new Map,me==null||me({ReactiveElement:U}),(E.reactiveElementVersions??(E.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const K=globalThis,Ve=t=>t,ae=K.trustedTypes,Be=ae?ae.createPolicy("lit-html",{createHTML:t=>t}):void 0,rt="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,ot="?"+C,Nt=`<${ot}>`,I=document,Y=()=>I.createComment(""),Z=t=>t===null||typeof t!="object"&&typeof t!="function",Ue=Array.isArray,Pt=t=>Ue(t)||typeof(t==null?void 0:t[Symbol.iterator])=="function",ge=`[ 	
\f\r]`,F=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Fe=/-->/g,Ge=/>/g,N=RegExp(`>|${ge}(?:([^\\s"'>=/]+)(${ge}*=${ge}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ke=/'/g,Je=/"/g,it=/^(?:script|style|textarea|title)$/i,Tt=t=>(e,...s)=>({_$litType$:t,strings:e,values:s}),y=Tt(1),M=Symbol.for("lit-noChange"),m=Symbol.for("lit-nothing"),Ye=new WeakMap,T=I.createTreeWalker(I,129);function nt(t,e){if(!Ue(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return Be!==void 0?Be.createHTML(e):e}const kt=(t,e)=>{const s=t.length-1,o=[];let r,i=e===2?"<svg>":e===3?"<math>":"",n=F;for(let a=0;a<s;a++){const d=t[a];let l,f,c=-1,g=0;for(;g<d.length&&(n.lastIndex=g,f=n.exec(d),f!==null);)g=n.lastIndex,n===F?f[1]==="!--"?n=Fe:f[1]!==void 0?n=Ge:f[2]!==void 0?(it.test(f[2])&&(r=RegExp("</"+f[2],"g")),n=N):f[3]!==void 0&&(n=N):n===N?f[0]===">"?(n=r??F,c=-1):f[1]===void 0?c=-2:(c=n.lastIndex-f[2].length,l=f[1],n=f[3]===void 0?N:f[3]==='"'?Je:Ke):n===Je||n===Ke?n=N:n===Fe||n===Ge?n=F:(n=N,r=void 0);const w=n===N&&t[a+1].startsWith("/>")?" ":"";i+=n===F?d+Nt:c>=0?(o.push(l),d.slice(0,c)+rt+d.slice(c)+C+w):d+C+(c===-2?a:w)}return[nt(t,i+(t[s]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),o]};class X{constructor({strings:e,_$litType$:s},o){let r;this.parts=[];let i=0,n=0;const a=e.length-1,d=this.parts,[l,f]=kt(e,s);if(this.el=X.createElement(l,o),T.currentNode=this.el.content,s===2||s===3){const c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(r=T.nextNode())!==null&&d.length<a;){if(r.nodeType===1){if(r.hasAttributes())for(const c of r.getAttributeNames())if(c.endsWith(rt)){const g=f[n++],w=r.getAttribute(c).split(C),D=/([.?@])?(.*)/.exec(g);d.push({type:1,index:i,name:D[2],strings:w,ctor:D[1]==="."?Dt:D[1]==="?"?Ut:D[1]==="@"?Rt:le}),r.removeAttribute(c)}else c.startsWith(C)&&(d.push({type:6,index:i}),r.removeAttribute(c));if(it.test(r.tagName)){const c=r.textContent.split(C),g=c.length-1;if(g>0){r.textContent=ae?ae.emptyScript:"";for(let w=0;w<g;w++)r.append(c[w],Y()),T.nextNode(),d.push({type:2,index:++i});r.append(c[g],Y())}}}else if(r.nodeType===8)if(r.data===ot)d.push({type:2,index:i});else{let c=-1;for(;(c=r.data.indexOf(C,c+1))!==-1;)d.push({type:7,index:i}),c+=C.length-1}i++}}static createElement(e,s){const o=I.createElement("template");return o.innerHTML=e,o}}function W(t,e,s=t,o){var n,a;if(e===M)return e;let r=o!==void 0?(n=s._$Co)==null?void 0:n[o]:s._$Cl;const i=Z(e)?void 0:e._$litDirective$;return(r==null?void 0:r.constructor)!==i&&((a=r==null?void 0:r._$AO)==null||a.call(r,!1),i===void 0?r=void 0:(r=new i(t),r._$AT(t,s,o)),o!==void 0?(s._$Co??(s._$Co=[]))[o]=r:s._$Cl=r),r!==void 0&&(e=W(t,r._$AS(t,e.values),r,o)),e}class It{constructor(e,s){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:s},parts:o}=this._$AD,r=((e==null?void 0:e.creationScope)??I).importNode(s,!0);T.currentNode=r;let i=T.nextNode(),n=0,a=0,d=o[0];for(;d!==void 0;){if(n===d.index){let l;d.type===2?l=new ee(i,i.nextSibling,this,e):d.type===1?l=new d.ctor(i,d.name,d.strings,this,e):d.type===6&&(l=new Mt(i,this,e)),this._$AV.push(l),d=o[++a]}n!==(d==null?void 0:d.index)&&(i=T.nextNode(),n++)}return T.currentNode=I,r}p(e){let s=0;for(const o of this._$AV)o!==void 0&&(o.strings!==void 0?(o._$AI(e,o,s),s+=o.strings.length-2):o._$AI(e[s])),s++}}class ee{get _$AU(){var e;return((e=this._$AM)==null?void 0:e._$AU)??this._$Cv}constructor(e,s,o,r){this.type=2,this._$AH=m,this._$AN=void 0,this._$AA=e,this._$AB=s,this._$AM=o,this.options=r,this._$Cv=(r==null?void 0:r.isConnected)??!0}get parentNode(){let e=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=s.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,s=this){e=W(this,e,s),Z(e)?e===m||e==null||e===""?(this._$AH!==m&&this._$AR(),this._$AH=m):e!==this._$AH&&e!==M&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Pt(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==m&&Z(this._$AH)?this._$AA.nextSibling.data=e:this.T(I.createTextNode(e)),this._$AH=e}$(e){var i;const{values:s,_$litType$:o}=e,r=typeof o=="number"?this._$AC(e):(o.el===void 0&&(o.el=X.createElement(nt(o.h,o.h[0]),this.options)),o);if(((i=this._$AH)==null?void 0:i._$AD)===r)this._$AH.p(s);else{const n=new It(r,this),a=n.u(this.options);n.p(s),this.T(a),this._$AH=n}}_$AC(e){let s=Ye.get(e.strings);return s===void 0&&Ye.set(e.strings,s=new X(e)),s}k(e){Ue(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let o,r=0;for(const i of e)r===s.length?s.push(o=new ee(this.O(Y()),this.O(Y()),this,this.options)):o=s[r],o._$AI(i),r++;r<s.length&&(this._$AR(o&&o._$AB.nextSibling,r),s.length=r)}_$AR(e=this._$AA.nextSibling,s){var o;for((o=this._$AP)==null?void 0:o.call(this,!1,!0,s);e!==this._$AB;){const r=Ve(e).nextSibling;Ve(e).remove(),e=r}}setConnected(e){var s;this._$AM===void 0&&(this._$Cv=e,(s=this._$AP)==null||s.call(this,e))}}class le{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,s,o,r,i){this.type=1,this._$AH=m,this._$AN=void 0,this.element=e,this.name=s,this._$AM=r,this.options=i,o.length>2||o[0]!==""||o[1]!==""?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=m}_$AI(e,s=this,o,r){const i=this.strings;let n=!1;if(i===void 0)e=W(this,e,s,0),n=!Z(e)||e!==this._$AH&&e!==M,n&&(this._$AH=e);else{const a=e;let d,l;for(e=i[0],d=0;d<i.length-1;d++)l=W(this,a[o+d],s,d),l===M&&(l=this._$AH[d]),n||(n=!Z(l)||l!==this._$AH[d]),l===m?e=m:e!==m&&(e+=(l??"")+i[d+1]),this._$AH[d]=l}n&&!r&&this.j(e)}j(e){e===m?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class Dt extends le{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===m?void 0:e}}class Ut extends le{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==m)}}class Rt extends le{constructor(e,s,o,r,i){super(e,s,o,r,i),this.type=5}_$AI(e,s=this){if((e=W(this,e,s,0)??m)===M)return;const o=this._$AH,r=e===m&&o!==m||e.capture!==o.capture||e.once!==o.once||e.passive!==o.passive,i=e!==m&&(o===m||r);r&&this.element.removeEventListener(this.name,this,o),i&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var s;typeof this._$AH=="function"?this._$AH.call(((s=this.options)==null?void 0:s.host)??this.element,e):this._$AH.handleEvent(e)}}class Mt{constructor(e,s,o){this.element=e,this.type=6,this._$AN=void 0,this._$AM=s,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(e){W(this,e)}}const $e=K.litHtmlPolyfillSupport;$e==null||$e(X,ee),(K.litHtmlVersions??(K.litHtmlVersions=[])).push("3.3.3");const Wt=(t,e,s)=>{const o=(s==null?void 0:s.renderBefore)??e;let r=o._$litPart$;if(r===void 0){const i=(s==null?void 0:s.renderBefore)??null;o._$litPart$=r=new ee(e.insertBefore(Y(),i),i,void 0,s??{})}return r._$AI(t),r};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const k=globalThis;let x=class extends U{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var s;const e=super.createRenderRoot();return(s=this.renderOptions).renderBefore??(s.renderBefore=e.firstChild),e}update(e){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Wt(s,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return M}};var tt;x._$litElement$=!0,x.finalized=!0,(tt=k.litElementHydrateSupport)==null||tt.call(k,{LitElement:x});const ye=k.litElementPolyfillSupport;ye==null||ye({LitElement:x});(k.litElementVersions??(k.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const q=t=>(e,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ht={attribute:!0,type:String,converter:ne,reflect:!1,hasChanged:De},Lt=(t=Ht,e,s)=>{const{kind:o,metadata:r}=s;let i=globalThis.litPropertyMetadata.get(r);if(i===void 0&&globalThis.litPropertyMetadata.set(r,i=new Map),o==="setter"&&((t=Object.create(t)).wrapped=!0),i.set(s.name,t),o==="accessor"){const{name:n}=s;return{set(a){const d=e.get.call(this);e.set.call(this,a),this.requestUpdate(n,d,t,!0,a)},init(a){return a!==void 0&&this.C(n,void 0,t,a),a}}}if(o==="setter"){const{name:n}=s;return function(a){const d=this[n];e.call(this,a),this.requestUpdate(n,d,t,!0,a)}}throw Error("Unsupported decorator location: "+o)};function S(t){return(e,s)=>typeof s=="object"?Lt(t,e,s):((o,r,i)=>{const n=r.hasOwnProperty(i);return r.constructor.createProperty(i,o),n?Object.getOwnPropertyDescriptor(r,i):void 0})(t,e,s)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ue(t){return S({...t,state:!0,attribute:!1})}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const jt=(t,e,s)=>(s.configurable=!0,s.enumerable=!0,Reflect.decorate&&typeof e!="object"&&Object.defineProperty(t,e,s),s);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function zt(t,e){return(s,o,r)=>{const i=n=>{var a;return((a=n.renderRoot)==null?void 0:a.querySelector(t))??null};return jt(s,o,{get(){return i(this)}})}}var qt=Object.defineProperty,Vt=(t,e,s)=>e in t?qt(t,e,{enumerable:!0,configurable:!0,writable:!0,value:s}):t[e]=s,be=(t,e,s)=>(Vt(t,typeof e!="symbol"?e+"":e,s),s),Bt=(t,e,s)=>{if(!e.has(t))throw TypeError("Cannot "+s)},_e=(t,e)=>{if(Object(e)!==e)throw TypeError('Cannot use the "in" operator on this value');return t.has(e)},se=(t,e,s)=>{if(e.has(t))throw TypeError("Cannot add the same private member more than once");e instanceof WeakSet?e.add(t):e.set(t,s)},Ze=(t,e,s)=>(Bt(t,e,"access private method"),s);/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function at(t,e){return Object.is(t,e)}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */let v=null,J=!1,ie=1;const de=Symbol("SIGNAL");function R(t){const e=v;return v=t,e}function Ft(){return v}function Gt(){return J}const Re={version:0,lastCleanEpoch:0,dirty:!1,producerNode:void 0,producerLastReadVersion:void 0,producerIndexOfThis:void 0,nextProducerIndex:0,liveConsumerNode:void 0,liveConsumerIndexOfThis:void 0,consumerAllowSignalWrites:!1,consumerIsAlwaysLive:!1,producerMustRecompute:()=>!1,producerRecomputeValue:()=>{},consumerMarkedDirty:()=>{},consumerOnSignalRead:()=>{}};function he(t){if(J)throw new Error(typeof ngDevMode<"u"&&ngDevMode?"Assertion error: signal read during notification phase":"");if(v===null)return;v.consumerOnSignalRead(t);const e=v.nextProducerIndex++;if(H(v),e<v.producerNode.length&&v.producerNode[e]!==t&&Ae(v)){const s=v.producerNode[e];pe(s,v.producerIndexOfThis[e])}v.producerNode[e]!==t&&(v.producerNode[e]=t,v.producerIndexOfThis[e]=Ae(v)?lt(t,v,e):0),v.producerLastReadVersion[e]=t.version}function Kt(){ie++}function dt(t){if(!(!t.dirty&&t.lastCleanEpoch===ie)){if(!t.producerMustRecompute(t)&&!Qt(t)){t.dirty=!1,t.lastCleanEpoch=ie;return}t.producerRecomputeValue(t),t.dirty=!1,t.lastCleanEpoch=ie}}function ct(t){if(t.liveConsumerNode===void 0)return;const e=J;J=!0;try{for(const s of t.liveConsumerNode)s.dirty||Yt(s)}finally{J=e}}function Jt(){return(v==null?void 0:v.consumerAllowSignalWrites)!==!1}function Yt(t){var e;t.dirty=!0,ct(t),(e=t.consumerMarkedDirty)==null||e.call(t.wrapper??t)}function Zt(t){return t&&(t.nextProducerIndex=0),R(t)}function Xt(t,e){if(R(e),!(!t||t.producerNode===void 0||t.producerIndexOfThis===void 0||t.producerLastReadVersion===void 0)){if(Ae(t))for(let s=t.nextProducerIndex;s<t.producerNode.length;s++)pe(t.producerNode[s],t.producerIndexOfThis[s]);for(;t.producerNode.length>t.nextProducerIndex;)t.producerNode.pop(),t.producerLastReadVersion.pop(),t.producerIndexOfThis.pop()}}function Qt(t){H(t);for(let e=0;e<t.producerNode.length;e++){const s=t.producerNode[e],o=t.producerLastReadVersion[e];if(o!==s.version||(dt(s),o!==s.version))return!0}return!1}function lt(t,e,s){var o;if(Me(t),H(t),t.liveConsumerNode.length===0){(o=t.watched)==null||o.call(t.wrapper);for(let r=0;r<t.producerNode.length;r++)t.producerIndexOfThis[r]=lt(t.producerNode[r],t,r)}return t.liveConsumerIndexOfThis.push(s),t.liveConsumerNode.push(e)-1}function pe(t,e){var s;if(Me(t),H(t),typeof ngDevMode<"u"&&ngDevMode&&e>=t.liveConsumerNode.length)throw new Error(`Assertion error: active consumer index ${e} is out of bounds of ${t.liveConsumerNode.length} consumers)`);if(t.liveConsumerNode.length===1){(s=t.unwatched)==null||s.call(t.wrapper);for(let r=0;r<t.producerNode.length;r++)pe(t.producerNode[r],t.producerIndexOfThis[r])}const o=t.liveConsumerNode.length-1;if(t.liveConsumerNode[e]=t.liveConsumerNode[o],t.liveConsumerIndexOfThis[e]=t.liveConsumerIndexOfThis[o],t.liveConsumerNode.length--,t.liveConsumerIndexOfThis.length--,e<t.liveConsumerNode.length){const r=t.liveConsumerIndexOfThis[e],i=t.liveConsumerNode[e];H(i),i.producerIndexOfThis[r]=e}}function Ae(t){var e;return t.consumerIsAlwaysLive||(((e=t==null?void 0:t.liveConsumerNode)==null?void 0:e.length)??0)>0}function H(t){t.producerNode??(t.producerNode=[]),t.producerIndexOfThis??(t.producerIndexOfThis=[]),t.producerLastReadVersion??(t.producerLastReadVersion=[])}function Me(t){t.liveConsumerNode??(t.liveConsumerNode=[]),t.liveConsumerIndexOfThis??(t.liveConsumerIndexOfThis=[])}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function ut(t){if(dt(t),he(t),t.value===Ce)throw t.error;return t.value}function es(t){const e=Object.create(ts);e.computation=t;const s=()=>ut(e);return s[de]=e,s}const we=Symbol("UNSET"),xe=Symbol("COMPUTING"),Ce=Symbol("ERRORED"),ts={...Re,value:we,dirty:!0,error:null,equal:at,producerMustRecompute(t){return t.value===we||t.value===xe},producerRecomputeValue(t){if(t.value===xe)throw new Error("Detected cycle in computations.");const e=t.value;t.value=xe;const s=Zt(t);let o,r=!1;try{o=t.computation.call(t.wrapper),r=e!==we&&e!==Ce&&t.equal.call(t.wrapper,e,o)}catch(i){o=Ce,t.error=i}finally{Xt(t,s)}if(r){t.value=e;return}t.value=o,t.version++}};/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function ss(){throw new Error}let rs=ss;function os(){rs()}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function is(t){const e=Object.create(ds);e.value=t;const s=()=>(he(e),e.value);return s[de]=e,s}function ns(){return he(this),this.value}function as(t,e){Jt()||os(),t.equal.call(t.wrapper,t.value,e)||(t.value=e,cs(t))}const ds={...Re,equal:at,value:void 0};function cs(t){t.version++,Kt(),ct(t)}/**
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
 */const $=Symbol("node");var A;(t=>{var e,s,o,r;class i{constructor(d,l={}){se(this,s),be(this,e);const c=is(d)[de];if(this[$]=c,c.wrapper=this,l){const g=l.equals;g&&(c.equal=g),c.watched=l[t.subtle.watched],c.unwatched=l[t.subtle.unwatched]}}get(){if(!(0,t.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.get");return ns.call(this[$])}set(d){if(!(0,t.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.set");if(Gt())throw new Error("Writes to signals not permitted during Watcher callback");const l=this[$];as(l,d)}}e=$,s=new WeakSet,t.isState=a=>typeof a=="object"&&_e(s,a),t.State=i;class n{constructor(d,l){se(this,r),be(this,o);const c=es(d)[de];if(c.consumerAllowSignalWrites=!0,this[$]=c,c.wrapper=this,l){const g=l.equals;g&&(c.equal=g),c.watched=l[t.subtle.watched],c.unwatched=l[t.subtle.unwatched]}}get(){if(!(0,t.isComputed)(this))throw new TypeError("Wrong receiver type for Signal.Computed.prototype.get");return ut(this[$])}}o=$,r=new WeakSet,t.isComputed=a=>typeof a=="object"&&_e(r,a),t.Computed=n,(a=>{var d,l,f,c;function g(p){let h,u=null;try{u=R(null),h=p()}finally{R(u)}return h}a.untrack=g;function w(p){var h;if(!(0,t.isComputed)(p)&&!(0,t.isWatcher)(p))throw new TypeError("Called introspectSources without a Computed or Watcher argument");return((h=p[$].producerNode)==null?void 0:h.map(u=>u.wrapper))??[]}a.introspectSources=w;function D(p){var h;if(!(0,t.isComputed)(p)&&!(0,t.isState)(p))throw new TypeError("Called introspectSinks without a Signal argument");return((h=p[$].liveConsumerNode)==null?void 0:h.map(u=>u.wrapper))??[]}a.introspectSinks=D;function vt(p){if(!(0,t.isComputed)(p)&&!(0,t.isState)(p))throw new TypeError("Called hasSinks without a Signal argument");const h=p[$].liveConsumerNode;return h?h.length>0:!1}a.hasSinks=vt;function mt(p){if(!(0,t.isComputed)(p)&&!(0,t.isWatcher)(p))throw new TypeError("Called hasSources without a Computed or Watcher argument");const h=p[$].producerNode;return h?h.length>0:!1}a.hasSources=mt;class gt{constructor(h){se(this,l),se(this,f),be(this,d);let u=Object.create(Re);u.wrapper=this,u.consumerMarkedDirty=h,u.consumerIsAlwaysLive=!0,u.consumerAllowSignalWrites=!1,u.producerNode=[],this[$]=u}watch(...h){if(!(0,t.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");Ze(this,f,c).call(this,h);const u=this[$];u.dirty=!1;const b=R(u);for(const te of h)he(te[$]);R(b)}unwatch(...h){if(!(0,t.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");Ze(this,f,c).call(this,h);const u=this[$];H(u);for(let b=u.producerNode.length-1;b>=0;b--)if(h.includes(u.producerNode[b].wrapper)){pe(u.producerNode[b],u.producerIndexOfThis[b]);const te=u.producerNode.length-1;if(u.producerNode[b]=u.producerNode[te],u.producerIndexOfThis[b]=u.producerIndexOfThis[te],u.producerNode.length--,u.producerIndexOfThis.length--,u.nextProducerIndex--,b<u.producerNode.length){const yt=u.producerIndexOfThis[b],He=u.producerNode[b];Me(He),He.liveConsumerIndexOfThis[yt]=b}}}getPending(){if(!(0,t.isWatcher)(this))throw new TypeError("Called getPending without Watcher receiver");return this[$].producerNode.filter(u=>u.dirty).map(u=>u.wrapper)}}d=$,l=new WeakSet,f=new WeakSet,c=function(p){for(const h of p)if(!(0,t.isComputed)(h)&&!(0,t.isState)(h))throw new TypeError("Called watch/unwatch without a Computed or State argument")},t.isWatcher=p=>_e(l,p),a.Watcher=gt;function $t(){var p;return(p=Ft())==null?void 0:p.wrapper}a.currentComputed=$t,a.watched=Symbol("watched"),a.unwatched=Symbol("unwatched")})(t.subtle||(t.subtle={}))})(A||(A={}));/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const ls=Symbol("SignalWatcherBrand"),us=new FinalizationRegistry((({watcher:t,signal:e})=>{t.unwatch(e)})),Xe=new WeakMap;function hs(t){return t[ls]===!0?(console.warn("SignalWatcher should not be applied to the same class more than once."),t):class extends t{constructor(){super(...arguments),this._$St=new A.State(0),this._$Si=!1,this._$So=!0,this._$Sh=new Set}_$Sl(){if(this._$Su!==void 0)return;this._$Sv=new A.Computed((()=>{this._$St.get(),super.performUpdate()}));const e=this._$Su=new A.subtle.Watcher((function(){const s=Xe.get(this);s!==void 0&&(s._$Si===!1&&s.requestUpdate(),this.watch())}));Xe.set(e,this),us.register(this,{watcher:e,signal:this._$Sv}),e.watch(this._$Sv)}_$Sp(){this._$Su!==void 0&&(this._$Su.unwatch(this._$Sv),this._$Sv=void 0,this._$Su=void 0)}performUpdate(){this.isUpdatePending&&(this._$Sl(),this._$Si=!0,this._$St.set(this._$St.get()+1),this._$Si=!1,this._$Sv.get())}update(e){try{this._$So?(this._$So=!1,super.update(e)):this._$Sh.forEach((s=>s.commit()))}finally{this.isUpdatePending=!1,this._$Sh.clear()}}requestUpdate(e,s,o){this._$So=!0,super.requestUpdate(e,s,o)}connectedCallback(){super.connectedCallback(),this.requestUpdate()}disconnectedCallback(){super.disconnectedCallback(),queueMicrotask((()=>{this.isConnected===!1&&this._$Sp()}))}_(e){this._$Sh.add(e);const s=this._$So;this.requestUpdate(),this._$So=s}m(e){this._$Sh.delete(e)}}}/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */A.State;A.Computed;const V=(t,e)=>new A.State(t,e),ps=(t,e)=>new A.Computed(t,e);class fs{constructor(e="/ws/deep"){this.ws=null,this.handlers=new Set,this.reconnectDelay=1e3,this.maxDelay=15e3,this.closedByUser=!1,this.status="closed";const s=location.protocol==="https:"?"wss":"ws";this.url=`${s}://${location.host}${e}`}connect(){this.closedByUser=!1,this.status="connecting",this.ws=new WebSocket(this.url),this.ws.onopen=()=>{this.status="open",this.reconnectDelay=1e3,this.emit({type:"_socket_open"})},this.ws.onmessage=e=>{try{this.emit(JSON.parse(e.data))}catch{}},this.ws.onclose=()=>{this.status="closed",this.emit({type:"_socket_close"}),this.closedByUser||this.scheduleReconnect()},this.ws.onerror=()=>{var e;return(e=this.ws)==null?void 0:e.close()}}scheduleReconnect(){setTimeout(()=>this.connect(),this.reconnectDelay),this.reconnectDelay=Math.min(this.reconnectDelay*1.6,this.maxDelay)}send(e){var s;((s=this.ws)==null?void 0:s.readyState)===WebSocket.OPEN&&this.ws.send(JSON.stringify(e))}on(e){return this.handlers.add(e),()=>this.handlers.delete(e)}emit(e){for(const s of this.handlers)s(e)}close(){var e;this.closedByUser=!0,(e=this.ws)==null||e.close()}}const Ee=new fs;let Oe=1;const Ne=V("closed"),_=V([]),P=V(!1),Pe=V([]),ht=V("—"),pt=V("");ps(()=>_.get().some(t=>t.streaming));function vs(t,e=null){!t.trim()&&!e||(_.set([..._.get(),{id:Oe++,role:"user",text:t,image:e}]),P.set(!0),Pe.set([]),Ee.send({type:"chat",text:t,mode:"auto",image:e}))}function ms(){return _.get().find(t=>t.streaming)}function Qe(t){_.set(_.get().map(e=>e.streaming?{...e,...t}:e))}function gs(t){switch(t.type){case"_socket_open":Ne.set("open");break;case"_socket_close":Ne.set("closed");break;case"thinking":P.set(!0);break;case"response_start":P.set(!0);break;case"token":{P.set(!1);const e=String(t.content??"");ms()?_.set(_.get().map(o=>o.streaming?{...o,text:o.text+e}:o)):_.set([..._.get(),{id:Oe++,role:"ai",text:e,streaming:!0}]);break}case"response_end":{P.set(!1);const e=t;e.model&&ht.set(e.model),Qe({streaming:!1,model:e.model,latency:e.latency});break}case"reasoning":{const e=t.step;e&&Pe.set([...Pe.get(),e]);break}case"error":{P.set(!1),Qe({streaming:!1}),_.set([..._.get(),{id:Oe++,role:"ai",text:`⚠ ${t.message??"error"}`}]);break}default:pt.set(t.type)}}let et=!1;function $s(){et||(et=!0,Ee.on(t=>gs(t)),Ee.connect())}async function ys(t){const e=await fetch(t);if(!e.ok)throw new Error(`${t} → ${e.status}`);return await e.json()}const bs=()=>ys("/api/status");var _s=Object.defineProperty,ws=Object.getOwnPropertyDescriptor,fe=(t,e,s,o)=>{for(var r=o>1?void 0:o?ws(e,s):e,i=t.length-1,n;i>=0;i--)(n=t[i])&&(r=(o?n(e,s,r):n(r))||r);return o&&r&&_s(e,s,r),r};let L=class extends x{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return y`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};L.styles=z`
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
  `;fe([S()],L.prototype,"variant",2);fe([S()],L.prototype,"size",2);fe([S({type:Boolean})],L.prototype,"disabled",2);L=fe([q("ds-button")],L);var xs=Object.defineProperty,Ss=Object.getOwnPropertyDescriptor,We=(t,e,s,o)=>{for(var r=o>1?void 0:o?Ss(e,s):e,i=t.length-1,n;i>=0;i--)(n=t[i])&&(r=(o?n(e,s,r):n(r))||r);return o&&r&&xs(e,s,r),r};let Q=class extends x{constructor(){super(...arguments),this.heading="",this.variant="solid"}render(){return y`
      <section class=${this.variant}>
        ${this.heading?y`<header><span>${this.heading}</span><slot name="actions"></slot></header>`:""}
        <div class="body"><slot></slot></div>
      </section>
    `}};Q.styles=z`
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
  `;We([S()],Q.prototype,"heading",2);We([S()],Q.prototype,"variant",2);Q=We([q("ds-panel")],Q);var As=Object.defineProperty,Cs=Object.getOwnPropertyDescriptor,B=(t,e,s,o)=>{for(var r=o>1?void 0:o?Cs(e,s):e,i=t.length-1,n;i>=0;i--)(n=t[i])&&(r=(o?n(e,s,r):n(r))||r);return o&&r&&As(e,s,r),r};let O=class extends x{constructor(){super(...arguments),this.label="",this.placeholder="",this.value="",this.type="text"}onInput(){this.value=this.input.value,this.dispatchEvent(new CustomEvent("ds-input",{detail:this.value,bubbles:!0,composed:!0}))}onKeydown(t){t.key==="Enter"&&this.dispatchEvent(new CustomEvent("ds-submit",{detail:this.value,bubbles:!0,composed:!0}))}render(){return y`
      ${this.label?y`<label>${this.label}</label>`:""}
      <input
        .type=${this.type}
        .value=${this.value}
        placeholder=${this.placeholder}
        @input=${this.onInput}
        @keydown=${this.onKeydown}
      />
    `}};O.styles=z`
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
  `;B([S()],O.prototype,"label",2);B([S()],O.prototype,"placeholder",2);B([S()],O.prototype,"value",2);B([S()],O.prototype,"type",2);B([zt("input")],O.prototype,"input",2);O=B([q("ds-field")],O);var Es=Object.defineProperty,Os=Object.getOwnPropertyDescriptor,ft=(t,e,s,o)=>{for(var r=o>1?void 0:o?Os(e,s):e,i=t.length-1,n;i>=0;i--)(n=t[i])&&(r=(o?n(e,s,r):n(r))||r);return o&&r&&Es(e,s,r),r};let Ns=0,re=null;function Se(t,e="info",s=6e3){re||(re=document.createElement("ds-toast-host"),document.body.appendChild(re)),re.push({id:++Ns,text:t,kind:e},s)}let ce=class extends x{constructor(){super(...arguments),this.items=[]}push(t,e){this.items=[...this.items,t],setTimeout(()=>this.dismiss(t.id),e)}dismiss(t){this.items=this.items.filter(e=>e.id!==t)}render(){return y`${this.items.map(t=>y`
        <div class="toast ${t.kind}">
          <span>${t.text}</span>
          <button class="x" @click=${()=>this.dismiss(t.id)} aria-label="Dismiss">✕</button>
        </div>
      `)}`}};ce.styles=z`
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
  `;ft([ue()],ce.prototype,"items",2);ce=ft([q("ds-toast-host")],ce);var Ps=Object.getOwnPropertyDescriptor,Ts=(t,e,s,o)=>{for(var r=o>1?void 0:o?Ps(e,s):e,i=t.length-1,n;i>=0;i--)(n=t[i])&&(r=n(r)||r);return r};let Te=class extends x{render(){return y`
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
          <ds-button @click=${()=>Se("Saved successfully","success")}>Success</ds-button>
          <ds-button @click=${()=>Se("Heads up — informational","info")}>Info</ds-button>
          <ds-button variant="danger" @click=${()=>Se("Something failed","danger")}>Danger</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Surfaces" variant="glass">
        <p style="margin:0;color:var(--ds-text-soft)">This panel uses the glass variant.</p>
      </ds-panel>

      <ds-panel heading="Color tokens">
        <div class="swatches">
          ${["--ds-bg","--ds-surface-1","--ds-surface-2","--ds-surface-3","--ds-accent","--ds-success","--ds-warning","--ds-danger","--ds-info"].map(t=>y`<div class="sw" style="background: var(${t})">${t.slice(5)}</div>`)}
        </div>
      </ds-panel>
    `}};Te.styles=z`
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
  `;Te=Ts([q("ds-gallery")],Te);var ks=Object.defineProperty,Is=Object.getOwnPropertyDescriptor,ve=(t,e,s,o)=>{for(var r=o>1?void 0:o?Is(e,s):e,i=t.length-1,n;i>=0;i--)(n=t[i])&&(r=(o?n(e,s,r):n(r))||r);return o&&r&&ks(e,s,r),r};let j=class extends hs(x){constructor(){super(...arguments),this.route=location.hash.slice(1)||"home",this.status="—",this.draft="",this.onHash=()=>{this.route=location.hash.slice(1)||"home"}}connectedCallback(){super.connectedCallback(),$s(),bs().then(t=>this.status=t.deep).catch(()=>this.status="offline"),window.addEventListener("hashchange",this.onHash)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("hashchange",this.onHash)}submit(){vs(this.draft),this.draft="";const t=this.renderRoot.querySelector("ds-field");t&&(t.value="")}render(){const t=Ne.get();return y`
      <header>
        <span class="dot ${t==="open"?"open":""}"></span>
        <span class="logo">DEEP</span>
        <span class="spacer"></span>
        <nav>
          <a href="#home">chat</a>
          <a href="#gallery">gallery</a>
        </nav>
        <span class="meta">${this.status} · ${ht.get()}</span>
      </header>
      <main>
        ${this.route==="gallery"?y`<ds-gallery></ds-gallery>`:y`
              <div class="probe">
                <div class="msgs">
                  ${_.get().map(e=>y`
                      <div class="msg ${e.role} ${e.streaming?"streaming":""}">
                        ${e.text}
                      </div>
                    `)}
                  ${P.get()?y`<div class="msg ai">…</div>`:""}
                </div>
                <div class="row">
                  <ds-field
                    placeholder="Message DEEP…"
                    @ds-input=${e=>this.draft=e.detail}
                    @ds-submit=${()=>this.submit()}
                  ></ds-field>
                  <ds-button variant="primary" @click=${()=>this.submit()}>Send</ds-button>
                </div>
                <span class="hint">ws: ${t} · last event: ${pt.get()||"—"}</span>
              </div>
            `}
      </main>
    `}};j.styles=z`
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
  `;ve([ue()],j.prototype,"route",2);ve([ue()],j.prototype,"status",2);ve([ue()],j.prototype,"draft",2);j=ve([q("deep-app")],j);
//# sourceMappingURL=index-BDqvELDu.js.map
