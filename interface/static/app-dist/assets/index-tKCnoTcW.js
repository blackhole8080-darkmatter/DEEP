(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))r(s);new MutationObserver(s=>{for(const o of s)if(o.type==="childList")for(const n of o.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&r(n)}).observe(document,{childList:!0,subtree:!0});function t(s){const o={};return s.integrity&&(o.integrity=s.integrity),s.referrerPolicy&&(o.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?o.credentials="include":s.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function r(s){if(s.ep)return;s.ep=!0;const o=t(s);fetch(s.href,o)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const V=globalThis,ie=V.ShadowRoot&&(V.ShadyCSS===void 0||V.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,oe=Symbol(),le=new WeakMap;let _e=class{constructor(e,t,r){if(this._$cssResult$=!0,r!==oe)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(ie&&e===void 0){const r=t!==void 0&&t.length===1;r&&(e=le.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),r&&le.set(t,e))}return e}toString(){return this.cssText}};const Pe=i=>new _e(typeof i=="string"?i:i+"",void 0,oe),D=(i,...e)=>{const t=i.length===1?i[0]:e.reduce((r,s,o)=>r+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+i[o+1],i[0]);return new _e(t,i,oe)},Oe=(i,e)=>{if(ie)i.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const t of e){const r=document.createElement("style"),s=V.litNonce;s!==void 0&&r.setAttribute("nonce",s),r.textContent=t.cssText,i.appendChild(r)}},ce=ie?i=>i:i=>i instanceof CSSStyleSheet?(e=>{let t="";for(const r of e.cssRules)t+=r.cssText;return Pe(t)})(i):i;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:Ce,defineProperty:De,getOwnPropertyDescriptor:Ue,getOwnPropertyNames:ke,getOwnPropertySymbols:Te,getPrototypeOf:Me}=Object,b=globalThis,he=b.trustedTypes,He=he?he.emptyScript:"",G=b.reactiveElementPolyfillSupport,N=(i,e)=>i,K={toAttribute(i,e){switch(e){case Boolean:i=i?He:null;break;case Object:case Array:i=i==null?i:JSON.stringify(i)}return i},fromAttribute(i,e){let t=i;switch(e){case Boolean:t=i!==null;break;case Number:t=i===null?null:Number(i);break;case Object:case Array:try{t=JSON.parse(i)}catch{t=null}}return t}},ne=(i,e)=>!Ce(i,e),pe={attribute:!0,type:String,converter:K,reflect:!1,useDefault:!1,hasChanged:ne};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),b.litPropertyMetadata??(b.litPropertyMetadata=new WeakMap);let S=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??(this.l=[])).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=pe){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const r=Symbol(),s=this.getPropertyDescriptor(e,r,t);s!==void 0&&De(this.prototype,e,s)}}static getPropertyDescriptor(e,t,r){const{get:s,set:o}=Ue(this.prototype,e)??{get(){return this[t]},set(n){this[t]=n}};return{get:s,set(n){const d=s==null?void 0:s.call(this);o==null||o.call(this,n),this.requestUpdate(e,d,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??pe}static _$Ei(){if(this.hasOwnProperty(N("elementProperties")))return;const e=Me(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(N("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(N("properties"))){const t=this.properties,r=[...ke(t),...Te(t)];for(const s of r)this.createProperty(s,t[s])}const e=this[Symbol.metadata];if(e!==null){const t=litPropertyMetadata.get(e);if(t!==void 0)for(const[r,s]of t)this.elementProperties.set(r,s)}this._$Eh=new Map;for(const[t,r]of this.elementProperties){const s=this._$Eu(t,r);s!==void 0&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const r=new Set(e.flat(1/0).reverse());for(const s of r)t.unshift(ce(s))}else e!==void 0&&t.push(ce(e));return t}static _$Eu(e,t){const r=t.attribute;return r===!1?void 0:typeof r=="string"?r:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(t=>t(this))}addController(e){var t;(this._$EO??(this._$EO=new Set)).add(e),this.renderRoot!==void 0&&this.isConnected&&((t=e.hostConnected)==null||t.call(e))}removeController(e){var t;(t=this._$EO)==null||t.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const r of t.keys())this.hasOwnProperty(r)&&(e.set(r,this[r]),delete this[r]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Oe(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(t=>{var r;return(r=t.hostConnected)==null?void 0:r.call(t)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(t=>{var r;return(r=t.hostDisconnected)==null?void 0:r.call(t)})}attributeChangedCallback(e,t,r){this._$AK(e,r)}_$ET(e,t){var o;const r=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,r);if(s!==void 0&&r.reflect===!0){const n=(((o=r.converter)==null?void 0:o.toAttribute)!==void 0?r.converter:K).toAttribute(t,r.type);this._$Em=e,n==null?this.removeAttribute(s):this.setAttribute(s,n),this._$Em=null}}_$AK(e,t){var o,n;const r=this.constructor,s=r._$Eh.get(e);if(s!==void 0&&this._$Em!==s){const d=r.getPropertyOptions(s),a=typeof d.converter=="function"?{fromAttribute:d.converter}:((o=d.converter)==null?void 0:o.fromAttribute)!==void 0?d.converter:K;this._$Em=s;const c=a.fromAttribute(t,d.type);this[s]=c??((n=this._$Ej)==null?void 0:n.get(s))??c,this._$Em=null}}requestUpdate(e,t,r,s=!1,o){var n;if(e!==void 0){const d=this.constructor;if(s===!1&&(o=this[e]),r??(r=d.getPropertyOptions(e)),!((r.hasChanged??ne)(o,t)||r.useDefault&&r.reflect&&o===((n=this._$Ej)==null?void 0:n.get(e))&&!this.hasAttribute(d._$Eu(e,r))))return;this.C(e,t,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:r,reflect:s,wrapped:o},n){r&&!(this._$Ej??(this._$Ej=new Map)).has(e)&&(this._$Ej.set(e,n??t??this[e]),o!==!0||n!==void 0)||(this._$AL.has(e)||(this.hasUpdated||r||(t=void 0),this._$AL.set(e,t)),s===!0&&this._$Em!==e&&(this._$Eq??(this._$Eq=new Set)).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var r;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[o,n]of this._$Ep)this[o]=n;this._$Ep=void 0}const s=this.constructor.elementProperties;if(s.size>0)for(const[o,n]of s){const{wrapped:d}=n,a=this[o];d!==!0||this._$AL.has(o)||a===void 0||this.C(o,void 0,n,a)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),(r=this._$EO)==null||r.forEach(s=>{var o;return(o=s.hostUpdate)==null?void 0:o.call(s)}),this.update(t)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(t)}willUpdate(e){}_$AE(e){var t;(t=this._$EO)==null||t.forEach(r=>{var s;return(s=r.hostUpdated)==null?void 0:s.call(r)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(t=>this._$ET(t,this[t]))),this._$EM()}updated(e){}firstUpdated(e){}};S.elementStyles=[],S.shadowRootOptions={mode:"open"},S[N("elementProperties")]=new Map,S[N("finalized")]=new Map,G==null||G({ReactiveElement:S}),(b.reactiveElementVersions??(b.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const R=globalThis,ue=i=>i,F=R.trustedTypes,fe=F?F.createPolicy("lit-html",{createHTML:i=>i}):void 0,we="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,Ae="?"+$,Ne=`<${Ae}>`,E=document,z=()=>E.createComment(""),j=i=>i===null||typeof i!="object"&&typeof i!="function",ae=Array.isArray,Re=i=>ae(i)||typeof(i==null?void 0:i[Symbol.iterator])=="function",X=`[ 	
\f\r]`,H=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ve=/-->/g,me=/>/g,w=RegExp(`>|${X}(?:([^\\s"'>=/]+)(${X}*=${X}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ge=/'/g,$e=/"/g,xe=/^(?:script|style|textarea|title)$/i,ze=i=>(e,...t)=>({_$litType$:i,strings:e,values:t}),u=ze(1),P=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),be=new WeakMap,A=E.createTreeWalker(E,129);function Ee(i,e){if(!ae(i)||!i.hasOwnProperty("raw"))throw Error("invalid template strings array");return fe!==void 0?fe.createHTML(e):e}const je=(i,e)=>{const t=i.length-1,r=[];let s,o=e===2?"<svg>":e===3?"<math>":"",n=H;for(let d=0;d<t;d++){const a=i[d];let c,p,l=-1,m=0;for(;m<a.length&&(n.lastIndex=m,p=n.exec(a),p!==null);)m=n.lastIndex,n===H?p[1]==="!--"?n=ve:p[1]!==void 0?n=me:p[2]!==void 0?(xe.test(p[2])&&(s=RegExp("</"+p[2],"g")),n=w):p[3]!==void 0&&(n=w):n===w?p[0]===">"?(n=s??H,l=-1):p[1]===void 0?l=-2:(l=n.lastIndex-p[2].length,c=p[1],n=p[3]===void 0?w:p[3]==='"'?$e:ge):n===$e||n===ge?n=w:n===ve||n===me?n=H:(n=w,s=void 0);const g=n===w&&i[d+1].startsWith("/>")?" ":"";o+=n===H?a+Ne:l>=0?(r.push(c),a.slice(0,l)+we+a.slice(l)+$+g):a+$+(l===-2?d:g)}return[Ee(i,o+(i[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),r]};class L{constructor({strings:e,_$litType$:t},r){let s;this.parts=[];let o=0,n=0;const d=e.length-1,a=this.parts,[c,p]=je(e,t);if(this.el=L.createElement(c,r),A.currentNode=this.el.content,t===2||t===3){const l=this.el.content.firstChild;l.replaceWith(...l.childNodes)}for(;(s=A.nextNode())!==null&&a.length<d;){if(s.nodeType===1){if(s.hasAttributes())for(const l of s.getAttributeNames())if(l.endsWith(we)){const m=p[n++],g=s.getAttribute(l).split($),q=/([.?@])?(.*)/.exec(m);a.push({type:1,index:o,name:q[2],strings:g,ctor:q[1]==="."?Be:q[1]==="?"?Ie:q[1]==="@"?qe:Y}),s.removeAttribute(l)}else l.startsWith($)&&(a.push({type:6,index:o}),s.removeAttribute(l));if(xe.test(s.tagName)){const l=s.textContent.split($),m=l.length-1;if(m>0){s.textContent=F?F.emptyScript:"";for(let g=0;g<m;g++)s.append(l[g],z()),A.nextNode(),a.push({type:2,index:++o});s.append(l[m],z())}}}else if(s.nodeType===8)if(s.data===Ae)a.push({type:2,index:o});else{let l=-1;for(;(l=s.data.indexOf($,l+1))!==-1;)a.push({type:7,index:o}),l+=$.length-1}o++}}static createElement(e,t){const r=E.createElement("template");return r.innerHTML=e,r}}function O(i,e,t=i,r){var n,d;if(e===P)return e;let s=r!==void 0?(n=t._$Co)==null?void 0:n[r]:t._$Cl;const o=j(e)?void 0:e._$litDirective$;return(s==null?void 0:s.constructor)!==o&&((d=s==null?void 0:s._$AO)==null||d.call(s,!1),o===void 0?s=void 0:(s=new o(i),s._$AT(i,t,r)),r!==void 0?(t._$Co??(t._$Co=[]))[r]=s:t._$Cl=s),s!==void 0&&(e=O(i,s._$AS(i,e.values),s,r)),e}class Le{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:r}=this._$AD,s=((e==null?void 0:e.creationScope)??E).importNode(t,!0);A.currentNode=s;let o=A.nextNode(),n=0,d=0,a=r[0];for(;a!==void 0;){if(n===a.index){let c;a.type===2?c=new I(o,o.nextSibling,this,e):a.type===1?c=new a.ctor(o,a.name,a.strings,this,e):a.type===6&&(c=new We(o,this,e)),this._$AV.push(c),a=r[++d]}n!==(a==null?void 0:a.index)&&(o=A.nextNode(),n++)}return A.currentNode=E,s}p(e){let t=0;for(const r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(e,r,t),t+=r.strings.length-2):r._$AI(e[t])),t++}}class I{get _$AU(){var e;return((e=this._$AM)==null?void 0:e._$AU)??this._$Cv}constructor(e,t,r,s){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=r,this.options=s,this._$Cv=(s==null?void 0:s.isConnected)??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return t!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=O(this,e,t),j(e)?e===h||e==null||e===""?(this._$AH!==h&&this._$AR(),this._$AH=h):e!==this._$AH&&e!==P&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Re(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==h&&j(this._$AH)?this._$AA.nextSibling.data=e:this.T(E.createTextNode(e)),this._$AH=e}$(e){var o;const{values:t,_$litType$:r}=e,s=typeof r=="number"?this._$AC(e):(r.el===void 0&&(r.el=L.createElement(Ee(r.h,r.h[0]),this.options)),r);if(((o=this._$AH)==null?void 0:o._$AD)===s)this._$AH.p(t);else{const n=new Le(s,this),d=n.u(this.options);n.p(t),this.T(d),this._$AH=n}}_$AC(e){let t=be.get(e.strings);return t===void 0&&be.set(e.strings,t=new L(e)),t}k(e){ae(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let r,s=0;for(const o of e)s===t.length?t.push(r=new I(this.O(z()),this.O(z()),this,this.options)):r=t[s],r._$AI(o),s++;s<t.length&&(this._$AR(r&&r._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){var r;for((r=this._$AP)==null?void 0:r.call(this,!1,!0,t);e!==this._$AB;){const s=ue(e).nextSibling;ue(e).remove(),e=s}}setConnected(e){var t;this._$AM===void 0&&(this._$Cv=e,(t=this._$AP)==null||t.call(this,e))}}class Y{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,r,s,o){this.type=1,this._$AH=h,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=o,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=h}_$AI(e,t=this,r,s){const o=this.strings;let n=!1;if(o===void 0)e=O(this,e,t,0),n=!j(e)||e!==this._$AH&&e!==P,n&&(this._$AH=e);else{const d=e;let a,c;for(e=o[0],a=0;a<o.length-1;a++)c=O(this,d[r+a],t,a),c===P&&(c=this._$AH[a]),n||(n=!j(c)||c!==this._$AH[a]),c===h?e=h:e!==h&&(e+=(c??"")+o[a+1]),this._$AH[a]=c}n&&!s&&this.j(e)}j(e){e===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class Be extends Y{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===h?void 0:e}}class Ie extends Y{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==h)}}class qe extends Y{constructor(e,t,r,s,o){super(e,t,r,s,o),this.type=5}_$AI(e,t=this){if((e=O(this,e,t,0)??h)===P)return;const r=this._$AH,s=e===h&&r!==h||e.capture!==r.capture||e.once!==r.once||e.passive!==r.passive,o=e!==h&&(r===h||s);s&&this.element.removeEventListener(this.name,this,r),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var t;typeof this._$AH=="function"?this._$AH.call(((t=this.options)==null?void 0:t.host)??this.element,e):this._$AH.handleEvent(e)}}class We{constructor(e,t,r){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(e){O(this,e)}}const Q=R.litHtmlPolyfillSupport;Q==null||Q(L,I),(R.litHtmlVersions??(R.litHtmlVersions=[])).push("3.3.3");const Ve=(i,e,t)=>{const r=(t==null?void 0:t.renderBefore)??e;let s=r._$litPart$;if(s===void 0){const o=(t==null?void 0:t.renderBefore)??null;r._$litPart$=s=new I(e.insertBefore(z(),o),o,void 0,t??{})}return s._$AI(i),s};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const x=globalThis;class f extends S{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var t;const e=super.createRenderRoot();return(t=this.renderOptions).renderBefore??(t.renderBefore=e.firstChild),e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Ve(t,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return P}}var ye;f._$litElement$=!0,f.finalized=!0,(ye=x.litElementHydrateSupport)==null||ye.call(x,{LitElement:f});const ee=x.litElementPolyfillSupport;ee==null||ee({LitElement:f});(x.litElementVersions??(x.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const U=i=>(e,t)=>{t!==void 0?t.addInitializer(()=>{customElements.define(i,e)}):customElements.define(i,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ke={attribute:!0,type:String,converter:K,reflect:!1,hasChanged:ne},Fe=(i=Ke,e,t)=>{const{kind:r,metadata:s}=t;let o=globalThis.litPropertyMetadata.get(s);if(o===void 0&&globalThis.litPropertyMetadata.set(s,o=new Map),r==="setter"&&((i=Object.create(i)).wrapped=!0),o.set(t.name,i),r==="accessor"){const{name:n}=t;return{set(d){const a=e.get.call(this);e.set.call(this,d),this.requestUpdate(n,a,i,!0,d)},init(d){return d!==void 0&&this.C(n,void 0,i,d),d}}}if(r==="setter"){const{name:n}=t;return function(d){const a=this[n];e.call(this,d),this.requestUpdate(n,a,i,!0,d)}}throw Error("Unsupported decorator location: "+r)};function v(i){return(e,t)=>typeof t=="object"?Fe(i,e,t):((r,s,o)=>{const n=s.hasOwnProperty(o);return s.constructor.createProperty(o,r),n?Object.getOwnPropertyDescriptor(s,o):void 0})(i,e,t)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function k(i){return v({...i,state:!0,attribute:!1})}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Je=(i,e,t)=>(t.configurable=!0,t.enumerable=!0,Reflect.decorate&&typeof e!="object"&&Object.defineProperty(i,e,t),t);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function Ye(i,e){return(t,r,s)=>{const o=n=>{var d;return((d=n.renderRoot)==null?void 0:d.querySelector(i))??null};return Je(t,r,{get(){return o(this)}})}}class Ze{constructor(e="/ws/deep"){this.ws=null,this.handlers=new Set,this.reconnectDelay=1e3,this.maxDelay=15e3,this.closedByUser=!1,this.status="closed";const t=location.protocol==="https:"?"wss":"ws";this.url=`${t}://${location.host}${e}`}connect(){this.closedByUser=!1,this.status="connecting",this.ws=new WebSocket(this.url),this.ws.onopen=()=>{this.status="open",this.reconnectDelay=1e3,this.emit({type:"_socket_open"})},this.ws.onmessage=e=>{try{this.emit(JSON.parse(e.data))}catch{}},this.ws.onclose=()=>{this.status="closed",this.emit({type:"_socket_close"}),this.closedByUser||this.scheduleReconnect()},this.ws.onerror=()=>{var e;return(e=this.ws)==null?void 0:e.close()}}scheduleReconnect(){setTimeout(()=>this.connect(),this.reconnectDelay),this.reconnectDelay=Math.min(this.reconnectDelay*1.6,this.maxDelay)}send(e){var t;((t=this.ws)==null?void 0:t.readyState)===WebSocket.OPEN&&this.ws.send(JSON.stringify(e))}on(e){return this.handlers.add(e),()=>this.handlers.delete(e)}emit(e){for(const t of this.handlers)t(e)}close(){var e;this.closedByUser=!0,(e=this.ws)==null||e.close()}}const te=new Ze;var Ge=Object.defineProperty,Xe=Object.getOwnPropertyDescriptor,Z=(i,e,t,r)=>{for(var s=r>1?void 0:r?Xe(e,t):e,o=i.length-1,n;o>=0;o--)(n=i[o])&&(s=(r?n(e,t,s):n(s))||s);return r&&s&&Ge(e,t,s),s};let C=class extends f{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return u`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};C.styles=D`
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
  `;Z([v()],C.prototype,"variant",2);Z([v()],C.prototype,"size",2);Z([v({type:Boolean})],C.prototype,"disabled",2);C=Z([U("ds-button")],C);var Qe=Object.defineProperty,et=Object.getOwnPropertyDescriptor,de=(i,e,t,r)=>{for(var s=r>1?void 0:r?et(e,t):e,o=i.length-1,n;o>=0;o--)(n=i[o])&&(s=(r?n(e,t,s):n(s))||s);return r&&s&&Qe(e,t,s),s};let B=class extends f{constructor(){super(...arguments),this.heading="",this.variant="solid"}render(){return u`
      <section class=${this.variant}>
        ${this.heading?u`<header><span>${this.heading}</span><slot name="actions"></slot></header>`:""}
        <div class="body"><slot></slot></div>
      </section>
    `}};B.styles=D`
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
  `;de([v()],B.prototype,"heading",2);de([v()],B.prototype,"variant",2);B=de([U("ds-panel")],B);var tt=Object.defineProperty,st=Object.getOwnPropertyDescriptor,T=(i,e,t,r)=>{for(var s=r>1?void 0:r?st(e,t):e,o=i.length-1,n;o>=0;o--)(n=i[o])&&(s=(r?n(e,t,s):n(s))||s);return r&&s&&tt(e,t,s),s};let y=class extends f{constructor(){super(...arguments),this.label="",this.placeholder="",this.value="",this.type="text"}onInput(){this.value=this.input.value,this.dispatchEvent(new CustomEvent("ds-input",{detail:this.value,bubbles:!0,composed:!0}))}onKeydown(i){i.key==="Enter"&&this.dispatchEvent(new CustomEvent("ds-submit",{detail:this.value,bubbles:!0,composed:!0}))}render(){return u`
      ${this.label?u`<label>${this.label}</label>`:""}
      <input
        .type=${this.type}
        .value=${this.value}
        placeholder=${this.placeholder}
        @input=${this.onInput}
        @keydown=${this.onKeydown}
      />
    `}};y.styles=D`
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
  `;T([v()],y.prototype,"label",2);T([v()],y.prototype,"placeholder",2);T([v()],y.prototype,"value",2);T([v()],y.prototype,"type",2);T([Ye("input")],y.prototype,"input",2);y=T([U("ds-field")],y);var rt=Object.defineProperty,it=Object.getOwnPropertyDescriptor,Se=(i,e,t,r)=>{for(var s=r>1?void 0:r?it(e,t):e,o=i.length-1,n;o>=0;o--)(n=i[o])&&(s=(r?n(e,t,s):n(s))||s);return r&&s&&rt(e,t,s),s};let ot=0,W=null;function se(i,e="info",t=6e3){W||(W=document.createElement("ds-toast-host"),document.body.appendChild(W)),W.push({id:++ot,text:i,kind:e},t)}let J=class extends f{constructor(){super(...arguments),this.items=[]}push(i,e){this.items=[...this.items,i],setTimeout(()=>this.dismiss(i.id),e)}dismiss(i){this.items=this.items.filter(e=>e.id!==i)}render(){return u`${this.items.map(i=>u`
        <div class="toast ${i.kind}">
          <span>${i.text}</span>
          <button class="x" @click=${()=>this.dismiss(i.id)} aria-label="Dismiss">✕</button>
        </div>
      `)}`}};J.styles=D`
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
  `;Se([k()],J.prototype,"items",2);J=Se([U("ds-toast-host")],J);var nt=Object.getOwnPropertyDescriptor,at=(i,e,t,r)=>{for(var s=r>1?void 0:r?nt(e,t):e,o=i.length-1,n;o>=0;o--)(n=i[o])&&(s=n(s)||s);return s};let re=class extends f{render(){return u`
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
          <ds-button @click=${()=>se("Saved successfully","success")}>Success</ds-button>
          <ds-button @click=${()=>se("Heads up — informational","info")}>Info</ds-button>
          <ds-button variant="danger" @click=${()=>se("Something failed","danger")}>Danger</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Surfaces" variant="glass">
        <p style="margin:0;color:var(--ds-text-soft)">This panel uses the glass variant.</p>
      </ds-panel>

      <ds-panel heading="Color tokens">
        <div class="swatches">
          ${["--ds-bg","--ds-surface-1","--ds-surface-2","--ds-surface-3","--ds-accent","--ds-success","--ds-warning","--ds-danger","--ds-info"].map(i=>u`<div class="sw" style="background: var(${i})">${i.slice(5)}</div>`)}
        </div>
      </ds-panel>
    `}};re.styles=D`
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
  `;re=at([U("ds-gallery")],re);var dt=Object.defineProperty,lt=Object.getOwnPropertyDescriptor,M=(i,e,t,r)=>{for(var s=r>1?void 0:r?lt(e,t):e,o=i.length-1,n;o>=0;o--)(n=i[o])&&(s=(r?n(e,t,s):n(s))||s);return r&&s&&dt(e,t,s),s};let _=class extends f{constructor(){super(...arguments),this.conn="closed",this.status="—",this.model="—",this.lastEvent="",this.route=location.hash.slice(1)||"home",this.onHash=()=>{this.route=location.hash.slice(1)||"home"}}connectedCallback(){super.connectedCallback(),this.off=te.on(i=>this.onMessage(i)),te.connect(),this.fetchStatus(),window.addEventListener("hashchange",this.onHash)}disconnectedCallback(){var i;super.disconnectedCallback(),(i=this.off)==null||i.call(this),te.close(),window.removeEventListener("hashchange",this.onHash)}onMessage(i){i.type==="_socket_open"?this.conn="open":i.type==="_socket_close"?this.conn="closed":this.lastEvent=i.type}async fetchStatus(){try{const e=await(await fetch("/api/status")).json();this.status=String(e.deep??"—"),this.model=String(e.model??"—")}catch{this.status="offline"}}render(){return u`
      <header>
        <span class="dot ${this.conn==="open"?"open":""}"></span>
        <span class="logo">DEEP</span>
        <span class="spacer"></span>
        <span class="meta">${this.status} · ${this.model}</span>
      </header>
      <main style=${this.route==="gallery"?"display:block;place-items:unset;overflow:auto":""}>
        ${this.route==="gallery"?u`<ds-gallery></ds-gallery>`:u`
              <div class="card">
                <h1>Modern shell online</h1>
                <p>This is the new Vite + Lit frontend (Phase 1).</p>
                <p>WebSocket: <code>${this.conn}</code></p>
                <p>Last live event: <code>${this.lastEvent||"(none yet)"}</code></p>
                <p>Design system: <a href="#gallery" style="color:var(--ds-accent)">open the gallery</a></p>
              </div>
            `}
      </main>
    `}};_.styles=D`
    :host {
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100%;
    }
    header {
      display: flex;
      align-items: center;
      gap: var(--ds-space-3);
      padding: var(--ds-space-3) var(--ds-space-5);
      border-bottom: 1px solid var(--ds-border);
      background: var(--ds-glass);
      -webkit-backdrop-filter: blur(var(--ds-blur-md));
      backdrop-filter: blur(var(--ds-blur-md));
    }
    .logo { font-weight: 700; letter-spacing: 0.02em; }
    .dot {
      width: 8px; height: 8px; border-radius: var(--ds-radius-pill);
      background: var(--ds-danger);
    }
    .dot.open { background: var(--ds-success); box-shadow: 0 0 8px var(--ds-success); }
    .spacer { flex: 1; }
    .meta { font-family: var(--ds-font-mono); font-size: var(--ds-text-sm); color: var(--ds-text-soft); }
    main {
      display: grid;
      place-items: center;
      padding: var(--ds-space-7);
    }
    .card {
      max-width: 520px;
      padding: var(--ds-space-6);
      background: var(--ds-surface-1);
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      box-shadow: var(--ds-elev-2);
      animation: rise var(--ds-dur-slow) var(--ds-ease-spring);
    }
    h1 { margin: 0 0 var(--ds-space-2); font-size: var(--ds-text-2xl); }
    p { margin: var(--ds-space-2) 0; color: var(--ds-text-soft); }
    code { font-family: var(--ds-font-mono); color: var(--ds-accent); }
    @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  `;M([k()],_.prototype,"conn",2);M([k()],_.prototype,"status",2);M([k()],_.prototype,"model",2);M([k()],_.prototype,"lastEvent",2);M([k()],_.prototype,"route",2);_=M([U("deep-app")],_);
//# sourceMappingURL=index-tKCnoTcW.js.map
