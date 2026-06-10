var Ri=Object.defineProperty;var Ci=(t,e,s)=>e in t?Ri(t,e,{enumerable:!0,configurable:!0,writable:!0,value:s}):t[e]=s;var O=(t,e,s)=>Ci(t,typeof e!="symbol"?e+"":e,s);(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))n(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const a of i.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&n(a)}).observe(document,{childList:!0,subtree:!0});function s(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function n(r){if(r.ep)return;r.ep=!0;const i=s(r);fetch(r.href,i)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Jt=globalThis,cr=Jt.ShadowRoot&&(Jt.ShadyCSS===void 0||Jt.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,dr=Symbol(),Qr=new WeakMap;let Mn=class{constructor(e,s,n){if(this._$cssResult$=!0,n!==dr)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=s}get styleSheet(){let e=this.o;const s=this.t;if(cr&&e===void 0){const n=s!==void 0&&s.length===1;n&&(e=Qr.get(s)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),n&&Qr.set(s,e))}return e}toString(){return this.cssText}};const Oi=t=>new Mn(typeof t=="string"?t:t+"",void 0,dr),se=(t,...e)=>{const s=t.length===1?t[0]:e.reduce((n,r,i)=>n+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+t[i+1],t[0]);return new Mn(s,t,dr)},Pi=(t,e)=>{if(cr)t.adoptedStyleSheets=e.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of e){const n=document.createElement("style"),r=Jt.litNonce;r!==void 0&&n.setAttribute("nonce",r),n.textContent=s.cssText,t.appendChild(n)}},Jr=cr?t=>t:t=>t instanceof CSSStyleSheet?(e=>{let s="";for(const n of e.cssRules)s+=n.cssText;return Oi(s)})(t):t;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:Di,defineProperty:Ni,getOwnPropertyDescriptor:Ii,getOwnPropertyNames:Li,getOwnPropertySymbols:Mi,getPrototypeOf:zi}=Object,Se=globalThis,en=Se.trustedTypes,Ui=en?en.emptyScript:"",Ms=Se.reactiveElementPolyfillSupport,kt=(t,e)=>t,ts={toAttribute(t,e){switch(e){case Boolean:t=t?Ui:null;break;case Object:case Array:t=t==null?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=t!==null;break;case Number:s=t===null?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch{s=null}}return s}},ur=(t,e)=>!Di(t,e),tn={attribute:!0,type:String,converter:ts,reflect:!1,useDefault:!1,hasChanged:ur};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),Se.litPropertyMetadata??(Se.litPropertyMetadata=new WeakMap);let Je=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??(this.l=[])).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,s=tn){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(e,s),!s.noAccessor){const n=Symbol(),r=this.getPropertyDescriptor(e,n,s);r!==void 0&&Ni(this.prototype,e,r)}}static getPropertyDescriptor(e,s,n){const{get:r,set:i}=Ii(this.prototype,e)??{get(){return this[s]},set(a){this[s]=a}};return{get:r,set(a){const c=r==null?void 0:r.call(this);i==null||i.call(this,a),this.requestUpdate(e,c,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??tn}static _$Ei(){if(this.hasOwnProperty(kt("elementProperties")))return;const e=zi(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(kt("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(kt("properties"))){const s=this.properties,n=[...Li(s),...Mi(s)];for(const r of n)this.createProperty(r,s[r])}const e=this[Symbol.metadata];if(e!==null){const s=litPropertyMetadata.get(e);if(s!==void 0)for(const[n,r]of s)this.elementProperties.set(n,r)}this._$Eh=new Map;for(const[s,n]of this.elementProperties){const r=this._$Eu(s,n);r!==void 0&&this._$Eh.set(r,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const s=[];if(Array.isArray(e)){const n=new Set(e.flat(1/0).reverse());for(const r of n)s.unshift(Jr(r))}else e!==void 0&&s.push(Jr(e));return s}static _$Eu(e,s){const n=s.attribute;return n===!1?void 0:typeof n=="string"?n:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(s=>this.enableUpdating=s),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(s=>s(this))}addController(e){var s;(this._$EO??(this._$EO=new Set)).add(e),this.renderRoot!==void 0&&this.isConnected&&((s=e.hostConnected)==null||s.call(e))}removeController(e){var s;(s=this._$EO)==null||s.delete(e)}_$E_(){const e=new Map,s=this.constructor.elementProperties;for(const n of s.keys())this.hasOwnProperty(n)&&(e.set(n,this[n]),delete this[n]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Pi(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(s=>{var n;return(n=s.hostConnected)==null?void 0:n.call(s)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(s=>{var n;return(n=s.hostDisconnected)==null?void 0:n.call(s)})}attributeChangedCallback(e,s,n){this._$AK(e,n)}_$ET(e,s){var i;const n=this.constructor.elementProperties.get(e),r=this.constructor._$Eu(e,n);if(r!==void 0&&n.reflect===!0){const a=(((i=n.converter)==null?void 0:i.toAttribute)!==void 0?n.converter:ts).toAttribute(s,n.type);this._$Em=e,a==null?this.removeAttribute(r):this.setAttribute(r,a),this._$Em=null}}_$AK(e,s){var i,a;const n=this.constructor,r=n._$Eh.get(e);if(r!==void 0&&this._$Em!==r){const c=n.getPropertyOptions(r),l=typeof c.converter=="function"?{fromAttribute:c.converter}:((i=c.converter)==null?void 0:i.fromAttribute)!==void 0?c.converter:ts;this._$Em=r;const p=l.fromAttribute(s,c.type);this[r]=p??((a=this._$Ej)==null?void 0:a.get(r))??p,this._$Em=null}}requestUpdate(e,s,n,r=!1,i){var a;if(e!==void 0){const c=this.constructor;if(r===!1&&(i=this[e]),n??(n=c.getPropertyOptions(e)),!((n.hasChanged??ur)(i,s)||n.useDefault&&n.reflect&&i===((a=this._$Ej)==null?void 0:a.get(e))&&!this.hasAttribute(c._$Eu(e,n))))return;this.C(e,s,n)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,s,{useDefault:n,reflect:r,wrapped:i},a){n&&!(this._$Ej??(this._$Ej=new Map)).has(e)&&(this._$Ej.set(e,a??s??this[e]),i!==!0||a!==void 0)||(this._$AL.has(e)||(this.hasUpdated||n||(s=void 0),this._$AL.set(e,s)),r===!0&&this._$Em!==e&&(this._$Eq??(this._$Eq=new Set)).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var n;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[i,a]of this._$Ep)this[i]=a;this._$Ep=void 0}const r=this.constructor.elementProperties;if(r.size>0)for(const[i,a]of r){const{wrapped:c}=a,l=this[i];c!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,a,l)}}let e=!1;const s=this._$AL;try{e=this.shouldUpdate(s),e?(this.willUpdate(s),(n=this._$EO)==null||n.forEach(r=>{var i;return(i=r.hostUpdate)==null?void 0:i.call(r)}),this.update(s)):this._$EM()}catch(r){throw e=!1,this._$EM(),r}e&&this._$AE(s)}willUpdate(e){}_$AE(e){var s;(s=this._$EO)==null||s.forEach(n=>{var r;return(r=n.hostUpdated)==null?void 0:r.call(n)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(s=>this._$ET(s,this[s]))),this._$EM()}updated(e){}firstUpdated(e){}};Je.elementStyles=[],Je.shadowRootOptions={mode:"open"},Je[kt("elementProperties")]=new Map,Je[kt("finalized")]=new Map,Ms==null||Ms({ReactiveElement:Je}),(Se.reactiveElementVersions??(Se.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const _t=globalThis,sn=t=>t,ss=_t.trustedTypes,rn=ss?ss.createPolicy("lit-html",{createHTML:t=>t}):void 0,zn="$lit$",$e=`lit$${Math.random().toFixed(9).slice(2)}$`,Un="?"+$e,Hi=`<${Un}>`,Le=document,Tt=()=>Le.createComment(""),St=t=>t===null||typeof t!="object"&&typeof t!="function",pr=Array.isArray,ji=t=>pr(t)||typeof(t==null?void 0:t[Symbol.iterator])=="function",zs=`[ 	
\f\r]`,bt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,nn=/-->/g,an=/>/g,Oe=RegExp(`>|${zs}(?:([^\\s"'>=/]+)(${zs}*=${zs}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),on=/'/g,ln=/"/g,Hn=/^(?:script|style|textarea|title)$/i,Fi=t=>(e,...s)=>({_$litType$:t,strings:e,values:s}),v=Fi(1),Me=Symbol.for("lit-noChange"),H=Symbol.for("lit-nothing"),cn=new WeakMap,Ne=Le.createTreeWalker(Le,129);function jn(t,e){if(!pr(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return rn!==void 0?rn.createHTML(e):e}const Bi=(t,e)=>{const s=t.length-1,n=[];let r,i=e===2?"<svg>":e===3?"<math>":"",a=bt;for(let c=0;c<s;c++){const l=t[c];let p,u,h=-1,m=0;for(;m<l.length&&(a.lastIndex=m,u=a.exec(l),u!==null);)m=a.lastIndex,a===bt?u[1]==="!--"?a=nn:u[1]!==void 0?a=an:u[2]!==void 0?(Hn.test(u[2])&&(r=RegExp("</"+u[2],"g")),a=Oe):u[3]!==void 0&&(a=Oe):a===Oe?u[0]===">"?(a=r??bt,h=-1):u[1]===void 0?h=-2:(h=a.lastIndex-u[2].length,p=u[1],a=u[3]===void 0?Oe:u[3]==='"'?ln:on):a===ln||a===on?a=Oe:a===nn||a===an?a=bt:(a=Oe,r=void 0);const R=a===Oe&&t[c+1].startsWith("/>")?" ":"";i+=a===bt?l+Hi:h>=0?(n.push(p),l.slice(0,h)+zn+l.slice(h)+$e+R):l+$e+(h===-2?c:R)}return[jn(t,i+(t[s]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),n]};class At{constructor({strings:e,_$litType$:s},n){let r;this.parts=[];let i=0,a=0;const c=e.length-1,l=this.parts,[p,u]=Bi(e,s);if(this.el=At.createElement(p,n),Ne.currentNode=this.el.content,s===2||s===3){const h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(r=Ne.nextNode())!==null&&l.length<c;){if(r.nodeType===1){if(r.hasAttributes())for(const h of r.getAttributeNames())if(h.endsWith(zn)){const m=u[a++],R=r.getAttribute(h).split($e),g=/([.?@])?(.*)/.exec(m);l.push({type:1,index:i,name:g[2],strings:R,ctor:g[1]==="."?qi:g[1]==="?"?Gi:g[1]==="@"?Vi:us}),r.removeAttribute(h)}else h.startsWith($e)&&(l.push({type:6,index:i}),r.removeAttribute(h));if(Hn.test(r.tagName)){const h=r.textContent.split($e),m=h.length-1;if(m>0){r.textContent=ss?ss.emptyScript:"";for(let R=0;R<m;R++)r.append(h[R],Tt()),Ne.nextNode(),l.push({type:2,index:++i});r.append(h[m],Tt())}}}else if(r.nodeType===8)if(r.data===Un)l.push({type:2,index:i});else{let h=-1;for(;(h=r.data.indexOf($e,h+1))!==-1;)l.push({type:7,index:i}),h+=$e.length-1}i++}}static createElement(e,s){const n=Le.createElement("template");return n.innerHTML=e,n}}function st(t,e,s=t,n){var a,c;if(e===Me)return e;let r=n!==void 0?(a=s._$Co)==null?void 0:a[n]:s._$Cl;const i=St(e)?void 0:e._$litDirective$;return(r==null?void 0:r.constructor)!==i&&((c=r==null?void 0:r._$AO)==null||c.call(r,!1),i===void 0?r=void 0:(r=new i(t),r._$AT(t,s,n)),n!==void 0?(s._$Co??(s._$Co=[]))[n]=r:s._$Cl=r),r!==void 0&&(e=st(t,r._$AS(t,e.values),r,n)),e}class Wi{constructor(e,s){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:s},parts:n}=this._$AD,r=((e==null?void 0:e.creationScope)??Le).importNode(s,!0);Ne.currentNode=r;let i=Ne.nextNode(),a=0,c=0,l=n[0];for(;l!==void 0;){if(a===l.index){let p;l.type===2?p=new Ot(i,i.nextSibling,this,e):l.type===1?p=new l.ctor(i,l.name,l.strings,this,e):l.type===6&&(p=new Yi(i,this,e)),this._$AV.push(p),l=n[++c]}a!==(l==null?void 0:l.index)&&(i=Ne.nextNode(),a++)}return Ne.currentNode=Le,r}p(e){let s=0;for(const n of this._$AV)n!==void 0&&(n.strings!==void 0?(n._$AI(e,n,s),s+=n.strings.length-2):n._$AI(e[s])),s++}}class Ot{get _$AU(){var e;return((e=this._$AM)==null?void 0:e._$AU)??this._$Cv}constructor(e,s,n,r){this.type=2,this._$AH=H,this._$AN=void 0,this._$AA=e,this._$AB=s,this._$AM=n,this.options=r,this._$Cv=(r==null?void 0:r.isConnected)??!0}get parentNode(){let e=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=s.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,s=this){e=st(this,e,s),St(e)?e===H||e==null||e===""?(this._$AH!==H&&this._$AR(),this._$AH=H):e!==this._$AH&&e!==Me&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):ji(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==H&&St(this._$AH)?this._$AA.nextSibling.data=e:this.T(Le.createTextNode(e)),this._$AH=e}$(e){var i;const{values:s,_$litType$:n}=e,r=typeof n=="number"?this._$AC(e):(n.el===void 0&&(n.el=At.createElement(jn(n.h,n.h[0]),this.options)),n);if(((i=this._$AH)==null?void 0:i._$AD)===r)this._$AH.p(s);else{const a=new Wi(r,this),c=a.u(this.options);a.p(s),this.T(c),this._$AH=a}}_$AC(e){let s=cn.get(e.strings);return s===void 0&&cn.set(e.strings,s=new At(e)),s}k(e){pr(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let n,r=0;for(const i of e)r===s.length?s.push(n=new Ot(this.O(Tt()),this.O(Tt()),this,this.options)):n=s[r],n._$AI(i),r++;r<s.length&&(this._$AR(n&&n._$AB.nextSibling,r),s.length=r)}_$AR(e=this._$AA.nextSibling,s){var n;for((n=this._$AP)==null?void 0:n.call(this,!1,!0,s);e!==this._$AB;){const r=sn(e).nextSibling;sn(e).remove(),e=r}}setConnected(e){var s;this._$AM===void 0&&(this._$Cv=e,(s=this._$AP)==null||s.call(this,e))}}let us=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,s,n,r,i){this.type=1,this._$AH=H,this._$AN=void 0,this.element=e,this.name=s,this._$AM=r,this.options=i,n.length>2||n[0]!==""||n[1]!==""?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=H}_$AI(e,s=this,n,r){const i=this.strings;let a=!1;if(i===void 0)e=st(this,e,s,0),a=!St(e)||e!==this._$AH&&e!==Me,a&&(this._$AH=e);else{const c=e;let l,p;for(e=i[0],l=0;l<i.length-1;l++)p=st(this,c[n+l],s,l),p===Me&&(p=this._$AH[l]),a||(a=!St(p)||p!==this._$AH[l]),p===H?e=H:e!==H&&(e+=(p??"")+i[l+1]),this._$AH[l]=p}a&&!r&&this.j(e)}j(e){e===H?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},qi=class extends us{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===H?void 0:e}},Gi=class extends us{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==H)}},Vi=class extends us{constructor(e,s,n,r,i){super(e,s,n,r,i),this.type=5}_$AI(e,s=this){if((e=st(this,e,s,0)??H)===Me)return;const n=this._$AH,r=e===H&&n!==H||e.capture!==n.capture||e.once!==n.once||e.passive!==n.passive,i=e!==H&&(n===H||r);r&&this.element.removeEventListener(this.name,this,n),i&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var s;typeof this._$AH=="function"?this._$AH.call(((s=this.options)==null?void 0:s.host)??this.element,e):this._$AH.handleEvent(e)}},Yi=class{constructor(e,s,n){this.element=e,this.type=6,this._$AN=void 0,this._$AM=s,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(e){st(this,e)}};const Us=_t.litHtmlPolyfillSupport;Us==null||Us(At,Ot),(_t.litHtmlVersions??(_t.litHtmlVersions=[])).push("3.3.3");const Zi=(t,e,s)=>{const n=(s==null?void 0:s.renderBefore)??e;let r=n._$litPart$;if(r===void 0){const i=(s==null?void 0:s.renderBefore)??null;n._$litPart$=r=new Ot(e.insertBefore(Tt(),i),i,void 0,s??{})}return r._$AI(t),r};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ie=globalThis;let V=class extends Je{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var s;const e=super.createRenderRoot();return(s=this.renderOptions).renderBefore??(s.renderBefore=e.firstChild),e}update(e){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Zi(s,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return Me}};var Ln;V._$litElement$=!0,V.finalized=!0,(Ln=Ie.litElementHydrateSupport)==null||Ln.call(Ie,{LitElement:V});const Hs=Ie.litElementPolyfillSupport;Hs==null||Hs({LitElement:V});(Ie.litElementVersions??(Ie.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const re=t=>(e,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ki={attribute:!0,type:String,converter:ts,reflect:!1,hasChanged:ur},Xi=(t=Ki,e,s)=>{const{kind:n,metadata:r}=s;let i=globalThis.litPropertyMetadata.get(r);if(i===void 0&&globalThis.litPropertyMetadata.set(r,i=new Map),n==="setter"&&((t=Object.create(t)).wrapped=!0),i.set(s.name,t),n==="accessor"){const{name:a}=s;return{set(c){const l=e.get.call(this);e.set.call(this,c),this.requestUpdate(a,l,t,!0,c)},init(c){return c!==void 0&&this.C(a,void 0,t,c),c}}}if(n==="setter"){const{name:a}=s;return function(c){const l=this[a];e.call(this,c),this.requestUpdate(a,l,t,!0,c)}}throw Error("Unsupported decorator location: "+n)};function le(t){return(e,s)=>typeof s=="object"?Xi(t,e,s):((n,r,i)=>{const a=r.hasOwnProperty(i);return r.constructor.createProperty(i,n),a?Object.getOwnPropertyDescriptor(r,i):void 0})(t,e,s)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function W(t){return le({...t,state:!0,attribute:!1})}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Qi=(t,e,s)=>(s.configurable=!0,s.enumerable=!0,Reflect.decorate&&typeof e!="object"&&Object.defineProperty(t,e,s),s);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ps(t,e){return(s,n,r)=>{const i=a=>{var c;return((c=a.renderRoot)==null?void 0:c.querySelector(t))??null};return Qi(s,n,{get(){return i(this)}})}}var Ji=Object.defineProperty,ea=(t,e,s)=>e in t?Ji(t,e,{enumerable:!0,configurable:!0,writable:!0,value:s}):t[e]=s,js=(t,e,s)=>(ea(t,typeof e!="symbol"?e+"":e,s),s),ta=(t,e,s)=>{if(!e.has(t))throw TypeError("Cannot "+s)},Fs=(t,e)=>{if(Object(e)!==e)throw TypeError('Cannot use the "in" operator on this value');return t.has(e)},Yt=(t,e,s)=>{if(e.has(t))throw TypeError("Cannot add the same private member more than once");e instanceof WeakSet?e.add(t):e.set(t,s)},dn=(t,e,s)=>(ta(t,e,"access private method"),s);/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Fn(t,e){return Object.is(t,e)}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */let U=null,$t=!1,es=1;const rs=Symbol("SIGNAL");function tt(t){const e=U;return U=t,e}function sa(){return U}function ra(){return $t}const hr={version:0,lastCleanEpoch:0,dirty:!1,producerNode:void 0,producerLastReadVersion:void 0,producerIndexOfThis:void 0,nextProducerIndex:0,liveConsumerNode:void 0,liveConsumerIndexOfThis:void 0,consumerAllowSignalWrites:!1,consumerIsAlwaysLive:!1,producerMustRecompute:()=>!1,producerRecomputeValue:()=>{},consumerMarkedDirty:()=>{},consumerOnSignalRead:()=>{}};function hs(t){if($t)throw new Error(typeof ngDevMode<"u"&&ngDevMode?"Assertion error: signal read during notification phase":"");if(U===null)return;U.consumerOnSignalRead(t);const e=U.nextProducerIndex++;if(rt(U),e<U.producerNode.length&&U.producerNode[e]!==t&&Ks(U)){const s=U.producerNode[e];fs(s,U.producerIndexOfThis[e])}U.producerNode[e]!==t&&(U.producerNode[e]=t,U.producerIndexOfThis[e]=Ks(U)?qn(t,U,e):0),U.producerLastReadVersion[e]=t.version}function na(){es++}function Bn(t){if(!(!t.dirty&&t.lastCleanEpoch===es)){if(!t.producerMustRecompute(t)&&!ca(t)){t.dirty=!1,t.lastCleanEpoch=es;return}t.producerRecomputeValue(t),t.dirty=!1,t.lastCleanEpoch=es}}function Wn(t){if(t.liveConsumerNode===void 0)return;const e=$t;$t=!0;try{for(const s of t.liveConsumerNode)s.dirty||aa(s)}finally{$t=e}}function ia(){return(U==null?void 0:U.consumerAllowSignalWrites)!==!1}function aa(t){var e;t.dirty=!0,Wn(t),(e=t.consumerMarkedDirty)==null||e.call(t.wrapper??t)}function oa(t){return t&&(t.nextProducerIndex=0),tt(t)}function la(t,e){if(tt(e),!(!t||t.producerNode===void 0||t.producerIndexOfThis===void 0||t.producerLastReadVersion===void 0)){if(Ks(t))for(let s=t.nextProducerIndex;s<t.producerNode.length;s++)fs(t.producerNode[s],t.producerIndexOfThis[s]);for(;t.producerNode.length>t.nextProducerIndex;)t.producerNode.pop(),t.producerLastReadVersion.pop(),t.producerIndexOfThis.pop()}}function ca(t){rt(t);for(let e=0;e<t.producerNode.length;e++){const s=t.producerNode[e],n=t.producerLastReadVersion[e];if(n!==s.version||(Bn(s),n!==s.version))return!0}return!1}function qn(t,e,s){var n;if(fr(t),rt(t),t.liveConsumerNode.length===0){(n=t.watched)==null||n.call(t.wrapper);for(let r=0;r<t.producerNode.length;r++)t.producerIndexOfThis[r]=qn(t.producerNode[r],t,r)}return t.liveConsumerIndexOfThis.push(s),t.liveConsumerNode.push(e)-1}function fs(t,e){var s;if(fr(t),rt(t),typeof ngDevMode<"u"&&ngDevMode&&e>=t.liveConsumerNode.length)throw new Error(`Assertion error: active consumer index ${e} is out of bounds of ${t.liveConsumerNode.length} consumers)`);if(t.liveConsumerNode.length===1){(s=t.unwatched)==null||s.call(t.wrapper);for(let r=0;r<t.producerNode.length;r++)fs(t.producerNode[r],t.producerIndexOfThis[r])}const n=t.liveConsumerNode.length-1;if(t.liveConsumerNode[e]=t.liveConsumerNode[n],t.liveConsumerIndexOfThis[e]=t.liveConsumerIndexOfThis[n],t.liveConsumerNode.length--,t.liveConsumerIndexOfThis.length--,e<t.liveConsumerNode.length){const r=t.liveConsumerIndexOfThis[e],i=t.liveConsumerNode[e];rt(i),i.producerIndexOfThis[r]=e}}function Ks(t){var e;return t.consumerIsAlwaysLive||(((e=t==null?void 0:t.liveConsumerNode)==null?void 0:e.length)??0)>0}function rt(t){t.producerNode??(t.producerNode=[]),t.producerIndexOfThis??(t.producerIndexOfThis=[]),t.producerLastReadVersion??(t.producerLastReadVersion=[])}function fr(t){t.liveConsumerNode??(t.liveConsumerNode=[]),t.liveConsumerIndexOfThis??(t.liveConsumerIndexOfThis=[])}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function Gn(t){if(Bn(t),hs(t),t.value===Xs)throw t.error;return t.value}function da(t){const e=Object.create(ua);e.computation=t;const s=()=>Gn(e);return s[rs]=e,s}const Bs=Symbol("UNSET"),Ws=Symbol("COMPUTING"),Xs=Symbol("ERRORED"),ua={...hr,value:Bs,dirty:!0,error:null,equal:Fn,producerMustRecompute(t){return t.value===Bs||t.value===Ws},producerRecomputeValue(t){if(t.value===Ws)throw new Error("Detected cycle in computations.");const e=t.value;t.value=Ws;const s=oa(t);let n,r=!1;try{n=t.computation.call(t.wrapper),r=e!==Bs&&e!==Xs&&t.equal.call(t.wrapper,e,n)}catch(i){n=Xs,t.error=i}finally{la(t,s)}if(r){t.value=e;return}t.value=n,t.version++}};/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function pa(){throw new Error}let ha=pa;function fa(){ha()}/**
 * @license
 * Copyright Google LLC All Rights Reserved.
 *
 * Use of this source code is governed by an MIT-style license that can be
 * found in the LICENSE file at https://angular.io/license
 */function ga(t){const e=Object.create(va);e.value=t;const s=()=>(hs(e),e.value);return s[rs]=e,s}function ma(){return hs(this),this.value}function ba(t,e){ia()||fa(),t.equal.call(t.wrapper,t.value,e)||(t.value=e,ya(t))}const va={...hr,equal:Fn,value:void 0};function ya(t){t.version++,na(),Wn(t)}/**
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
 */const Y=Symbol("node");var ye;(t=>{var e,s,n,r;class i{constructor(l,p={}){Yt(this,s),js(this,e);const h=ga(l)[rs];if(this[Y]=h,h.wrapper=this,p){const m=p.equals;m&&(h.equal=m),h.watched=p[t.subtle.watched],h.unwatched=p[t.subtle.unwatched]}}get(){if(!(0,t.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.get");return ma.call(this[Y])}set(l){if(!(0,t.isState)(this))throw new TypeError("Wrong receiver type for Signal.State.prototype.set");if(ra())throw new Error("Writes to signals not permitted during Watcher callback");const p=this[Y];ba(p,l)}}e=Y,s=new WeakSet,t.isState=c=>typeof c=="object"&&Fs(s,c),t.State=i;class a{constructor(l,p){Yt(this,r),js(this,n);const h=da(l)[rs];if(h.consumerAllowSignalWrites=!0,this[Y]=h,h.wrapper=this,p){const m=p.equals;m&&(h.equal=m),h.watched=p[t.subtle.watched],h.unwatched=p[t.subtle.unwatched]}}get(){if(!(0,t.isComputed)(this))throw new TypeError("Wrong receiver type for Signal.Computed.prototype.get");return Gn(this[Y])}}n=Y,r=new WeakSet,t.isComputed=c=>typeof c=="object"&&Fs(r,c),t.Computed=a,(c=>{var l,p,u,h;function m(T){let k,y=null;try{y=tt(null),k=T()}finally{tt(y)}return k}c.untrack=m;function R(T){var k;if(!(0,t.isComputed)(T)&&!(0,t.isWatcher)(T))throw new TypeError("Called introspectSources without a Computed or Watcher argument");return((k=T[Y].producerNode)==null?void 0:k.map(y=>y.wrapper))??[]}c.introspectSources=R;function g(T){var k;if(!(0,t.isComputed)(T)&&!(0,t.isState)(T))throw new TypeError("Called introspectSinks without a Signal argument");return((k=T[Y].liveConsumerNode)==null?void 0:k.map(y=>y.wrapper))??[]}c.introspectSinks=g;function K(T){if(!(0,t.isComputed)(T)&&!(0,t.isState)(T))throw new TypeError("Called hasSinks without a Signal argument");const k=T[Y].liveConsumerNode;return k?k.length>0:!1}c.hasSinks=K;function E(T){if(!(0,t.isComputed)(T)&&!(0,t.isWatcher)(T))throw new TypeError("Called hasSources without a Computed or Watcher argument");const k=T[Y].producerNode;return k?k.length>0:!1}c.hasSources=E;class ie{constructor(k){Yt(this,p),Yt(this,u),js(this,l);let y=Object.create(hr);y.wrapper=this,y.consumerMarkedDirty=k,y.consumerIsAlwaysLive=!0,y.consumerAllowSignalWrites=!1,y.producerNode=[],this[Y]=y}watch(...k){if(!(0,t.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");dn(this,u,h).call(this,k);const y=this[Y];y.dirty=!1;const S=tt(y);for(const ae of k)hs(ae[Y]);tt(S)}unwatch(...k){if(!(0,t.isWatcher)(this))throw new TypeError("Called unwatch without Watcher receiver");dn(this,u,h).call(this,k);const y=this[Y];rt(y);for(let S=y.producerNode.length-1;S>=0;S--)if(k.includes(y.producerNode[S].wrapper)){fs(y.producerNode[S],y.producerIndexOfThis[S]);const ae=y.producerNode.length-1;if(y.producerNode[S]=y.producerNode[ae],y.producerIndexOfThis[S]=y.producerIndexOfThis[ae],y.producerNode.length--,y.producerIndexOfThis.length--,y.nextProducerIndex--,S<y.producerNode.length){const dt=y.producerIndexOfThis[S],ut=y.producerNode[S];fr(ut),ut.liveConsumerIndexOfThis[dt]=S}}}getPending(){if(!(0,t.isWatcher)(this))throw new TypeError("Called getPending without Watcher receiver");return this[Y].producerNode.filter(y=>y.dirty).map(y=>y.wrapper)}}l=Y,p=new WeakSet,u=new WeakSet,h=function(T){for(const k of T)if(!(0,t.isComputed)(k)&&!(0,t.isState)(k))throw new TypeError("Called watch/unwatch without a Computed or State argument")},t.isWatcher=T=>Fs(p,T),c.Watcher=ie;function te(){var T;return(T=sa())==null?void 0:T.wrapper}c.currentComputed=te,c.watched=Symbol("watched"),c.unwatched=Symbol("unwatched")})(t.subtle||(t.subtle={}))})(ye||(ye={}));/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const xa=Symbol("SignalWatcherBrand"),wa=new FinalizationRegistry((({watcher:t,signal:e})=>{t.unwatch(e)})),un=new WeakMap;function Vn(t){return t[xa]===!0?(console.warn("SignalWatcher should not be applied to the same class more than once."),t):class extends t{constructor(){super(...arguments),this._$St=new ye.State(0),this._$Si=!1,this._$So=!0,this._$Sh=new Set}_$Sl(){if(this._$Su!==void 0)return;this._$Sv=new ye.Computed((()=>{this._$St.get(),super.performUpdate()}));const e=this._$Su=new ye.subtle.Watcher((function(){const s=un.get(this);s!==void 0&&(s._$Si===!1&&s.requestUpdate(),this.watch())}));un.set(e,this),wa.register(this,{watcher:e,signal:this._$Sv}),e.watch(this._$Sv)}_$Sp(){this._$Su!==void 0&&(this._$Su.unwatch(this._$Sv),this._$Sv=void 0,this._$Su=void 0)}performUpdate(){this.isUpdatePending&&(this._$Sl(),this._$Si=!0,this._$St.set(this._$St.get()+1),this._$Si=!1,this._$Sv.get())}update(e){try{this._$So?(this._$So=!1,super.update(e)):this._$Sh.forEach((s=>s.commit()))}finally{this.isUpdatePending=!1,this._$Sh.clear()}}requestUpdate(e,s,n){this._$So=!0,super.requestUpdate(e,s,n)}connectedCallback(){super.connectedCallback(),this.requestUpdate()}disconnectedCallback(){super.disconnectedCallback(),queueMicrotask((()=>{this.isConnected===!1&&this._$Sp()}))}_(e){this._$Sh.add(e);const s=this._$So;this.requestUpdate(),this._$So=s}m(e){this._$Sh.delete(e)}}}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const ka={CHILD:2},_a=t=>(...e)=>({_$litDirective$:t,values:e});let $a=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,s,n){this._$Ct=e,this._$AM=s,this._$Ci=n}_$AS(e,s){return this.update(e,s)}update(e,s){return this.render(...s)}};/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */ye.State;ye.Computed;const ot=(t,e)=>new ye.State(t,e),Ta=(t,e)=>new ye.Computed(t,e);class Sa{constructor(e="/ws/deep"){this.ws=null,this.handlers=new Set,this.reconnectDelay=1e3,this.maxDelay=15e3,this.closedByUser=!1,this.status="closed";const s=location.protocol==="https:"?"wss":"ws";this.url=`${s}://${location.host}${e}`}connect(){this.closedByUser=!1,this.status="connecting",this.ws=new WebSocket(this.url),this.ws.onopen=()=>{this.status="open",this.reconnectDelay=1e3,this.emit({type:"_socket_open"})},this.ws.onmessage=e=>{try{this.emit(JSON.parse(e.data))}catch{}},this.ws.onclose=()=>{this.status="closed",this.emit({type:"_socket_close"}),this.closedByUser||this.scheduleReconnect()},this.ws.onerror=()=>{var e;return(e=this.ws)==null?void 0:e.close()}}scheduleReconnect(){setTimeout(()=>this.connect(),this.reconnectDelay),this.reconnectDelay=Math.min(this.reconnectDelay*1.6,this.maxDelay)}send(e){var s;((s=this.ws)==null?void 0:s.readyState)===WebSocket.OPEN&&this.ws.send(JSON.stringify(e))}on(e){return this.handlers.add(e),()=>this.handlers.delete(e)}emit(e){for(const s of this.handlers)s(e)}close(){var e;this.closedByUser=!0,(e=this.ws)==null||e.close()}}const Qs=new Sa;let Js=1;const er=ot("closed"),ne=ot([]),Te=ot(!1),ns=ot([]),Yn=ot("—"),Aa=ot(""),Ea=Ta(()=>ne.get().some(t=>t.streaming));function Ra(t,e=null){!t.trim()&&!e||(ne.set([...ne.get(),{id:Js++,role:"user",text:t,image:e}]),Te.set(!0),ns.set([]),Qs.send({type:"chat",text:t,mode:"auto",image:e}))}function Ca(){return ne.get().find(t=>t.streaming)}function pn(t){ne.set(ne.get().map(e=>e.streaming?{...e,...t}:e))}function Oa(t){switch(t.type){case"_socket_open":er.set("open");break;case"_socket_close":er.set("closed");break;case"thinking":Te.set(!0);break;case"response_start":Te.set(!0);break;case"token":{Te.set(!1);const e=String(t.content??"");Ca()?ne.set(ne.get().map(n=>n.streaming?{...n,text:n.text+e}:n)):ne.set([...ne.get(),{id:Js++,role:"ai",text:e,streaming:!0}]);break}case"response_end":{Te.set(!1);const e=t;e.model&&Yn.set(e.model),pn({streaming:!1,model:e.model,latency:e.latency});break}case"reasoning":{const e=t.step;e&&ns.set([...ns.get(),e]);break}case"error":{Te.set(!1),pn({streaming:!1}),ne.set([...ne.get(),{id:Js++,role:"ai",text:`⚠ ${t.message??"error"}`}]);break}default:Aa.set(t.type)}}let hn=!1;function Pa(){hn||(hn=!0,Qs.on(t=>Oa(t)),Qs.connect())}async function Fe(t){const e=await fetch(t);if(!e.ok)throw new Error(`${t} → ${e.status}`);return await e.json()}const Da=()=>Fe("/api/status"),Zn=(t=!1)=>Fe(`/api/providers/health${t?"?force=true":""}`),Na=()=>Fe("/api/chem/table"),Ia=t=>Fe(`/api/chem/element/${t}`),La=()=>Fe("/api/physics/constants"),Ma=t=>Fe("/api/physics/formulas"),za=()=>Fe("/api/knowledge/list");async function fn(t){const e=new FormData;return e.append("file",t,t.name),await(await fetch("/api/knowledge/ingest",{method:"POST",body:e})).json()}var Ua=Object.defineProperty,Ha=Object.getOwnPropertyDescriptor,Kn=(t,e,s,n)=>{for(var r=n>1?void 0:n?Ha(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Ua(e,s,r),r};let ja=0,Zt=null;function B(t,e="info",s=6e3){Zt||(Zt=document.createElement("ds-toast-host"),document.body.appendChild(Zt)),Zt.push({id:++ja,text:t,kind:e},s)}let is=class extends V{constructor(){super(...arguments),this.items=[]}push(t,e){this.items=[...this.items,t],setTimeout(()=>this.dismiss(t.id),e)}dismiss(t){this.items=this.items.filter(e=>e.id!==t)}render(){return v`${this.items.map(t=>v`
        <div class="toast ${t.kind}">
          <span>${t.text}</span>
          <button class="x" @click=${()=>this.dismiss(t.id)} aria-label="Dismiss">✕</button>
        </div>
      `)}`}};is.styles=se`
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
  `;Kn([W()],is.prototype,"items",2);is=Kn([re("ds-toast-host")],is);const as=[];function Ee(t){as.some(e=>e.id===t.id)||as.push(t)}function Fa(t,e){const s=t.toLowerCase(),n=e.toLowerCase();let r=0,i=0;for(const a of s){const c=n.indexOf(a,r);if(c===-1)return-1;i+=c-r+(c===r?0:2),r=c+1}return i}function Ba(t){return t.trim()?as.map(e=>({c:e,s:Fa(t,e.label)})).filter(e=>e.s>=0).sort((e,s)=>e.s-s.s).map(e=>e.c):as}const Pt=t=>()=>{location.hash=t};Ee({id:"nav.chat",label:"Go to Chat",hint:"nav",run:Pt("home")});Ee({id:"nav.gallery",label:"Open Design Gallery",hint:"nav",run:Pt("gallery")});Ee({id:"nav.science",label:"Open Science (Periodic Table & Physics)",hint:"nav",run:Pt("science")});Ee({id:"nav.ops",label:"Open Ops (Providers · Security · Knowledge)",hint:"nav",run:Pt("ops")});Ee({id:"nav.agents",label:"Open Agents Board",hint:"nav",run:Pt("agents")});Ee({id:"nav.legacy",label:"Open Legacy UI (/ai)",hint:"nav",run:()=>{location.href="/ai"}});Ee({id:"sys.providers",label:"Check AI Provider Health",hint:"system",run:async()=>{try{const t=await Zn(!0),e=t.providers.filter(s=>s.configured&&!s.ok);e.length?B(`${e.length} provider(s) down: ${e.map(s=>s.provider).join(", ")}`,"danger",9e3):B(`All ${t.healthy}/${t.total} provider keys healthy`,"success")}catch{B("Provider health check failed","danger")}}});Ee({id:"sys.screen",label:"Describe My Screen",hint:"vision",run:async()=>{B("DEEP is looking at your screen…","info");try{const e=await(await fetch("/api/vision/screen",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({q:"Describe what's on this screen for Aryan, concisely."})})).json();e.ok?B(String(e.description).slice(0,280),"success",14e3):B(`Screen read failed: ${e.error}`,"danger")}catch{B("Screen read failed","danger")}}});var Wa=Object.defineProperty,qa=Object.getOwnPropertyDescriptor,gs=(t,e,s,n)=>{for(var r=n>1?void 0:n?qa(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Wa(e,s,r),r};let nt=class extends V{constructor(){super(...arguments),this.variant="ghost",this.size="md",this.disabled=!1}render(){return v`
      <button class="${this.variant} ${this.size}" ?disabled=${this.disabled}>
        <slot></slot>
      </button>
    `}};nt.styles=se`
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
  `;gs([le()],nt.prototype,"variant",2);gs([le()],nt.prototype,"size",2);gs([le({type:Boolean})],nt.prototype,"disabled",2);nt=gs([re("ds-button")],nt);var Ga=Object.defineProperty,Va=Object.getOwnPropertyDescriptor,gr=(t,e,s,n)=>{for(var r=n>1?void 0:n?Va(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Ga(e,s,r),r};let Et=class extends V{constructor(){super(...arguments),this.heading="",this.variant="solid"}render(){return v`
      <section class=${this.variant}>
        ${this.heading?v`<header><span>${this.heading}</span><slot name="actions"></slot></header>`:""}
        <div class="body"><slot></slot></div>
      </section>
    `}};Et.styles=se`
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
  `;gr([le()],Et.prototype,"heading",2);gr([le()],Et.prototype,"variant",2);Et=gr([re("ds-panel")],Et);var Ya=Object.defineProperty,Za=Object.getOwnPropertyDescriptor,lt=(t,e,s,n)=>{for(var r=n>1?void 0:n?Za(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Ya(e,s,r),r};let Ae=class extends V{constructor(){super(...arguments),this.label="",this.placeholder="",this.value="",this.type="text"}onInput(){this.value=this.input.value,this.dispatchEvent(new CustomEvent("ds-input",{detail:this.value,bubbles:!0,composed:!0}))}onKeydown(t){t.key==="Enter"&&this.dispatchEvent(new CustomEvent("ds-submit",{detail:this.value,bubbles:!0,composed:!0}))}render(){return v`
      ${this.label?v`<label>${this.label}</label>`:""}
      <input
        .type=${this.type}
        .value=${this.value}
        placeholder=${this.placeholder}
        @input=${this.onInput}
        @keydown=${this.onKeydown}
      />
    `}};Ae.styles=se`
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
  `;lt([le()],Ae.prototype,"label",2);lt([le()],Ae.prototype,"placeholder",2);lt([le()],Ae.prototype,"value",2);lt([le()],Ae.prototype,"type",2);lt([ps("input")],Ae.prototype,"input",2);Ae=lt([re("ds-field")],Ae);var Ka=Object.getOwnPropertyDescriptor,Xa=(t,e,s,n)=>{for(var r=n>1?void 0:n?Ka(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=a(r)||r);return r};let tr=class extends V{render(){return v`
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
          <ds-button @click=${()=>B("Saved successfully","success")}>Success</ds-button>
          <ds-button @click=${()=>B("Heads up — informational","info")}>Info</ds-button>
          <ds-button variant="danger" @click=${()=>B("Something failed","danger")}>Danger</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Surfaces" variant="glass">
        <p style="margin:0;color:var(--ds-text-soft)">This panel uses the glass variant.</p>
      </ds-panel>

      <ds-panel heading="Color tokens">
        <div class="swatches">
          ${["--ds-bg","--ds-surface-1","--ds-surface-2","--ds-surface-3","--ds-accent","--ds-success","--ds-warning","--ds-danger","--ds-info"].map(t=>v`<div class="sw" style="background: var(${t})">${t.slice(5)}</div>`)}
        </div>
      </ds-panel>
    `}};tr.styles=se`
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
  `;tr=Xa([re("ds-gallery")],tr);/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class sr extends $a{constructor(e){if(super(e),this.it=H,e.type!==ka.CHILD)throw Error(this.constructor.directiveName+"() can only be used in child bindings")}render(e){if(e===H||e==null)return this._t=void 0,this.it=e;if(e===Me)return e;if(typeof e!="string")throw Error(this.constructor.directiveName+"() called with a non-string value");if(e===this.it)return this._t;this.it=e;const s=[e];return s.raw=s,this._t={_$litType$:this.constructor.resultType,strings:s,values:[]}}}sr.directiveName="unsafeHTML",sr.resultType=1;const Qa=_a(sr);function mr(){return{async:!1,breaks:!1,extensions:null,gfm:!0,hooks:null,pedantic:!1,renderer:null,silent:!1,tokenizer:null,walkTokens:null}}var Be=mr();function Xn(t){Be=t}var De={exec:()=>null};function Ke(t){let e=[];return s=>{let n=Math.max(0,Math.min(3,s-1)),r=e[n];return r||(r=t(n),e[n]=r),r}}function A(t,e=""){let s=typeof t=="string"?t:t.source,n={replace:(r,i)=>{let a=typeof i=="string"?i:i.source;return a=a.replace(Q.caret,"$1"),s=s.replace(r,a),n},getRegex:()=>new RegExp(s,e)};return n}var Ja=((t="")=>{try{return!!new RegExp("(?<=1)(?<!1)"+t)}catch{return!1}})(),Q={codeRemoveIndent:/^(?: {1,4}| {0,3}\t)/gm,outputLinkReplace:/\\([\[\]])/g,indentCodeCompensation:/^(\s+)(?:```)/,beginningSpace:/^\s+/,endingHash:/#$/,startingSpaceChar:/^ /,endingSpaceChar:/ $/,nonSpaceChar:/[^ ]/,newLineCharGlobal:/\n/g,tabCharGlobal:/\t/g,multipleSpaceGlobal:/\s+/g,blankLine:/^[ \t]*$/,doubleBlankLine:/\n[ \t]*\n[ \t]*$/,blockquoteStart:/^ {0,3}>/,blockquoteSetextReplace:/\n {0,3}((?:=+|-+) *)(?=\n|$)/g,blockquoteSetextReplace2:/^ {0,3}>[ \t]?/gm,listReplaceNesting:/^ {1,4}(?=( {4})*[^ ])/g,listIsTask:/^\[[ xX]\] +\S/,listReplaceTask:/^\[[ xX]\] +/,listTaskCheckbox:/\[[ xX]\]/,anyLine:/\n.*\n/,hrefBrackets:/^<(.*)>$/,tableDelimiter:/[:|]/,tableAlignChars:/^\||\| *$/g,tableRowBlankLine:/\n[ \t]*$/,tableAlignRight:/^ *-+: *$/,tableAlignCenter:/^ *:-+: *$/,tableAlignLeft:/^ *:-+ *$/,startATag:/^<a /i,endATag:/^<\/a>/i,startPreScriptTag:/^<(pre|code|kbd|script)(\s|>)/i,endPreScriptTag:/^<\/(pre|code|kbd|script)(\s|>)/i,startAngleBracket:/^</,endAngleBracket:/>$/,pedanticHrefTitle:/^([^'"]*[^\s])\s+(['"])(.*)\2/,unicodeAlphaNumeric:/[\p{L}\p{N}]/u,escapeTest:/[&<>"']/,escapeReplace:/[&<>"']/g,escapeTestNoEncode:/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,escapeReplaceNoEncode:/[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,caret:/(^|[^\[])\^/g,percentDecode:/%25/g,findPipe:/\|/g,splitPipe:/ \|/,slashPipe:/\\\|/g,carriageReturn:/\r\n|\r/g,spaceLine:/^ +$/gm,notSpaceStart:/^\S*/,endingNewline:/\n$/,listItemRegex:t=>new RegExp(`^( {0,3}${t})((?:[	 ][^\\n]*)?(?:\\n|$))`),nextBulletRegex:Ke(t=>new RegExp(`^ {0,${t}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),hrRegex:Ke(t=>new RegExp(`^ {0,${t}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),fencesBeginRegex:Ke(t=>new RegExp(`^ {0,${t}}(?:\`\`\`|~~~)`)),headingBeginRegex:Ke(t=>new RegExp(`^ {0,${t}}#`)),htmlBeginRegex:Ke(t=>new RegExp(`^ {0,${t}}<(?:[a-z].*>|!--)`,"i")),blockquoteBeginRegex:Ke(t=>new RegExp(`^ {0,${t}}>`))},eo=/^(?:[ \t]*(?:\n|$))+/,to=/^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/,so=/^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/,Dt=/^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/,ro=/^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/,br=/ {0,3}(?:[*+-]|\d{1,9}[.)])/,Qn=/^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/,Jn=A(Qn).replace(/bull/g,br).replace(/blockCode/g,/(?: {4}| {0,3}\t)/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).replace(/\|table/g,"").getRegex(),no=A(Qn).replace(/bull/g,br).replace(/blockCode/g,/(?: {4}| {0,3}\t)/).replace(/fences/g,/ {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g,/ {0,3}>/).replace(/heading/g,/ {0,3}#{1,6}/).replace(/html/g,/ {0,3}<[^\n>]+>\n/).replace(/table/g,/ {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(),vr=/^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table| +\n)[^\n]+)*)/,io=/^[^\n]+/,yr=/(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/,ao=A(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label",yr).replace("title",/(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(),oo=A(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g,br).getRegex(),ms="address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul",xr=/<!--(?:-?>|[\s\S]*?(?:-->|$))/,lo=A("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n+|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>\\n*|$)|<![A-Z][\\s\\S]*?(?:>\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))","i").replace("comment",xr).replace("tag",ms).replace("attribute",/ +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(),ei=A(vr).replace("hr",Dt).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("|lheading","").replace("|table","").replace("blockquote"," {0,3}>").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",ms).getRegex(),co=A(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph",ei).getRegex(),wr={blockquote:co,code:to,def:ao,fences:so,heading:ro,hr:Dt,html:lo,lheading:Jn,list:oo,newline:eo,paragraph:ei,table:De,text:io},gn=A("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr",Dt).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("blockquote"," {0,3}>").replace("code","(?: {4}| {0,3}	)[^\\n]").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",ms).getRegex(),uo={...wr,lheading:no,table:gn,paragraph:A(vr).replace("hr",Dt).replace("heading"," {0,3}#{1,6}(?:\\s|$)").replace("|lheading","").replace("table",gn).replace("blockquote"," {0,3}>").replace("fences"," {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~{3,})[^\\n]*\\n").replace("list"," {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html","</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag",ms).getRegex()},po={...wr,html:A(`^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:"[^"]*"|'[^']*'|\\s[^'"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))`).replace("comment",xr).replace(/tag/g,"(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),def:/^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,heading:/^(#{1,6})(.*)(?:\n+|$)/,fences:De,lheading:/^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,paragraph:A(vr).replace("hr",Dt).replace("heading",` *#{1,6} *[^
]`).replace("lheading",Jn).replace("|table","").replace("blockquote"," {0,3}>").replace("|fences","").replace("|list","").replace("|html","").replace("|tag","").getRegex()},ho=/^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/,fo=/^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/,ti=/^( {2,}|\\)\n(?!\s*$)/,go=/^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/,ct=/[\p{P}\p{S}]/u,bs=/[\s\p{P}\p{S}]/u,kr=/[^\s\p{P}\p{S}]/u,mo=A(/^((?![*_])punctSpace)/,"u").replace(/punctSpace/g,bs).getRegex(),si=/(?!~)[\p{P}\p{S}]/u,bo=/(?!~)[\s\p{P}\p{S}]/u,vo=/(?:[^\s\p{P}\p{S}]|~)/u,yo=A(/link|precode-code|html/,"g").replace("link",/\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-",Ja?"(?<!`)()":"(^^|[^`])").replace("code",/(?<b>`+)[^`]+\k<b>(?!`)/).replace("html",/<(?! )[^<>]*?>/).getRegex(),ri=/^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/,xo=A(ri,"u").replace(/punct/g,ct).getRegex(),wo=A(ri,"u").replace(/punct/g,si).getRegex(),ni="^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)",ko=A(ni,"gu").replace(/notPunctSpace/g,kr).replace(/punctSpace/g,bs).replace(/punct/g,ct).getRegex(),_o=A(ni,"gu").replace(/notPunctSpace/g,vo).replace(/punctSpace/g,bo).replace(/punct/g,si).getRegex(),$o=A("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)","gu").replace(/notPunctSpace/g,kr).replace(/punctSpace/g,bs).replace(/punct/g,ct).getRegex(),To=A(/^~~?(?:((?!~)punct)|[^\s~])/,"u").replace(/punct/g,ct).getRegex(),So="^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)",Ao=A(So,"gu").replace(/notPunctSpace/g,kr).replace(/punctSpace/g,bs).replace(/punct/g,ct).getRegex(),Eo=A(/\\(punct)/,"gu").replace(/punct/g,ct).getRegex(),Ro=A(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme",/[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email",/[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(),Co=A(xr).replace("(?:-->|$)","-->").getRegex(),Oo=A("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment",Co).replace("attribute",/\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(),os=/(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/,Po=A(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label",os).replace("href",/<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*/).replace("title",/"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(),ii=A(/^!?\[(label)\]\[(ref)\]/).replace("label",os).replace("ref",yr).getRegex(),ai=A(/^!?\[(ref)\](?:\[\])?/).replace("ref",yr).getRegex(),Do=A("reflink|nolink(?!\\()","g").replace("reflink",ii).replace("nolink",ai).getRegex(),mn=/[hH][tT][tT][pP][sS]?|[fF][tT][pP]/,_r={_backpedal:De,anyPunctuation:Eo,autolink:Ro,blockSkip:yo,br:ti,code:fo,del:De,delLDelim:De,delRDelim:De,emStrongLDelim:xo,emStrongRDelimAst:ko,emStrongRDelimUnd:$o,escape:ho,link:Po,nolink:ai,punctuation:mo,reflink:ii,reflinkSearch:Do,tag:Oo,text:go,url:De},No={..._r,link:A(/^!?\[(label)\]\((.*?)\)/).replace("label",os).getRegex(),reflink:A(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label",os).getRegex()},rr={..._r,emStrongRDelimAst:_o,emStrongLDelim:wo,delLDelim:To,delRDelim:Ao,url:A(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol",mn).replace("email",/[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),_backpedal:/(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,del:/^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,text:A(/^([`~]+|[^`~])(?:(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol",mn).getRegex()},Io={...rr,br:A(ti).replace("{2,}","*").getRegex(),text:A(rr.text).replace("\\b_","\\b_| {2,}\\n").replace(/\{2,\}/g,"*").getRegex()},Kt={normal:wr,gfm:uo,pedantic:po},vt={normal:_r,gfm:rr,breaks:Io,pedantic:No},Lo={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"},bn=t=>Lo[t];function ge(t,e){if(e){if(Q.escapeTest.test(t))return t.replace(Q.escapeReplace,bn)}else if(Q.escapeTestNoEncode.test(t))return t.replace(Q.escapeReplaceNoEncode,bn);return t}function vn(t){try{t=encodeURI(t).replace(Q.percentDecode,"%")}catch{return null}return t}function yn(t,e){var i;let s=t.replace(Q.findPipe,(a,c,l)=>{let p=!1,u=c;for(;--u>=0&&l[u]==="\\";)p=!p;return p?"|":" |"}),n=s.split(Q.splitPipe),r=0;if(n[0].trim()||n.shift(),n.length>0&&!((i=n.at(-1))!=null&&i.trim())&&n.pop(),e)if(n.length>e)n.splice(e);else for(;n.length<e;)n.push("");for(;r<n.length;r++)n[r]=n[r].trim().replace(Q.slashPipe,"|");return n}function _e(t,e,s){let n=t.length;if(n===0)return"";let r=0;for(;r<n&&t.charAt(n-r-1)===e;)r++;return t.slice(0,n-r)}function xn(t){let e=t.split(`
`),s=e.length-1;for(;s>=0&&Q.blankLine.test(e[s]);)s--;return e.length-s<=2?t:e.slice(0,s+1).join(`
`)}function Mo(t,e){if(t.indexOf(e[1])===-1)return-1;let s=0;for(let n=0;n<t.length;n++)if(t[n]==="\\")n++;else if(t[n]===e[0])s++;else if(t[n]===e[1]&&(s--,s<0))return n;return s>0?-2:-1}function zo(t,e=0){let s=e,n="";for(let r of t)if(r==="	"){let i=4-s%4;n+=" ".repeat(i),s+=i}else n+=r,s++;return n}function wn(t,e,s,n,r){let i=e.href,a=e.title||null,c=t[1].replace(r.other.outputLinkReplace,"$1");n.state.inLink=!0;let l={type:t[0].charAt(0)==="!"?"image":"link",raw:s,href:i,title:a,text:c,tokens:n.inlineTokens(c)};return n.state.inLink=!1,l}function Uo(t,e,s){let n=t.match(s.other.indentCodeCompensation);if(n===null)return e;let r=n[1];return e.split(`
`).map(i=>{let a=i.match(s.other.beginningSpace);if(a===null)return i;let[c]=a;return c.length>=r.length?i.slice(r.length):i}).join(`
`)}var ls=class{constructor(t){O(this,"options");O(this,"rules");O(this,"lexer");this.options=t||Be}space(t){let e=this.rules.block.newline.exec(t);if(e&&e[0].length>0)return{type:"space",raw:e[0]}}code(t){let e=this.rules.block.code.exec(t);if(e){let s=this.options.pedantic?e[0]:xn(e[0]),n=s.replace(this.rules.other.codeRemoveIndent,"");return{type:"code",raw:s,codeBlockStyle:"indented",text:n}}}fences(t){let e=this.rules.block.fences.exec(t);if(e){let s=e[0],n=Uo(s,e[3]||"",this.rules);return{type:"code",raw:s,lang:e[2]?e[2].trim().replace(this.rules.inline.anyPunctuation,"$1"):e[2],text:n}}}heading(t){let e=this.rules.block.heading.exec(t);if(e){let s=e[2].trim();if(this.rules.other.endingHash.test(s)){let n=_e(s,"#");(this.options.pedantic||!n||this.rules.other.endingSpaceChar.test(n))&&(s=n.trim())}return{type:"heading",raw:_e(e[0],`
`),depth:e[1].length,text:s,tokens:this.lexer.inline(s)}}}hr(t){let e=this.rules.block.hr.exec(t);if(e)return{type:"hr",raw:_e(e[0],`
`)}}blockquote(t){let e=this.rules.block.blockquote.exec(t);if(e){let s=_e(e[0],`
`).split(`
`),n="",r="",i=[];for(;s.length>0;){let a=!1,c=[],l;for(l=0;l<s.length;l++)if(this.rules.other.blockquoteStart.test(s[l]))c.push(s[l]),a=!0;else if(!a)c.push(s[l]);else break;s=s.slice(l);let p=c.join(`
`),u=p.replace(this.rules.other.blockquoteSetextReplace,`
    $1`).replace(this.rules.other.blockquoteSetextReplace2,"");n=n?`${n}
${p}`:p,r=r?`${r}
${u}`:u;let h=this.lexer.state.top;if(this.lexer.state.top=!0,this.lexer.blockTokens(u,i,!0),this.lexer.state.top=h,s.length===0)break;let m=i.at(-1);if((m==null?void 0:m.type)==="code")break;if((m==null?void 0:m.type)==="blockquote"){let R=m,g=R.raw+`
`+s.join(`
`),K=this.blockquote(g);i[i.length-1]=K,n=n.substring(0,n.length-R.raw.length)+K.raw,r=r.substring(0,r.length-R.text.length)+K.text;break}else if((m==null?void 0:m.type)==="list"){let R=m,g=R.raw+`
`+s.join(`
`),K=this.list(g);i[i.length-1]=K,n=n.substring(0,n.length-m.raw.length)+K.raw,r=r.substring(0,r.length-R.raw.length)+K.raw,s=g.substring(i.at(-1).raw.length).split(`
`);continue}}return{type:"blockquote",raw:n,tokens:i,text:r}}}list(t){let e=this.rules.block.list.exec(t);if(e){let s=e[1].trim(),n=s.length>1,r={type:"list",raw:"",ordered:n,start:n?+s.slice(0,-1):"",loose:!1,items:[]};s=n?`\\d{1,9}\\${s.slice(-1)}`:`\\${s}`,this.options.pedantic&&(s=n?s:"[*+-]");let i=this.rules.other.listItemRegex(s),a=!1;for(;t;){let l=!1,p="",u="";if(!(e=i.exec(t))||this.rules.block.hr.test(t))break;p=e[0],t=t.substring(p.length);let h=zo(e[2].split(`
`,1)[0],e[1].length),m=t.split(`
`,1)[0],R=!h.trim(),g=0;if(this.options.pedantic?(g=2,u=h.trimStart()):R?g=e[1].length+1:(g=h.search(this.rules.other.nonSpaceChar),g=g>4?1:g,u=h.slice(g),g+=e[1].length),R&&this.rules.other.blankLine.test(m)&&(p+=m+`
`,t=t.substring(m.length+1),l=!0),!l){let K=this.rules.other.nextBulletRegex(g),E=this.rules.other.hrRegex(g),ie=this.rules.other.fencesBeginRegex(g),te=this.rules.other.headingBeginRegex(g),T=this.rules.other.htmlBeginRegex(g),k=this.rules.other.blockquoteBeginRegex(g);for(;t;){let y=t.split(`
`,1)[0],S;if(m=y,this.options.pedantic?(m=m.replace(this.rules.other.listReplaceNesting,"  "),S=m):S=m.replace(this.rules.other.tabCharGlobal,"    "),ie.test(m)||te.test(m)||T.test(m)||k.test(m)||K.test(m)||E.test(m))break;if(S.search(this.rules.other.nonSpaceChar)>=g||!m.trim())u+=`
`+S.slice(g);else{if(R||h.replace(this.rules.other.tabCharGlobal,"    ").search(this.rules.other.nonSpaceChar)>=4||ie.test(h)||te.test(h)||E.test(h))break;u+=`
`+m}R=!m.trim(),p+=y+`
`,t=t.substring(y.length+1),h=S.slice(g)}}r.loose||(a?r.loose=!0:this.rules.other.doubleBlankLine.test(p)&&(a=!0)),r.items.push({type:"list_item",raw:p,task:!!this.options.gfm&&this.rules.other.listIsTask.test(u),loose:!1,text:u,tokens:[]}),r.raw+=p}let c=r.items.at(-1);if(c)c.raw=c.raw.trimEnd(),c.text=c.text.trimEnd();else return;r.raw=r.raw.trimEnd();for(let l of r.items){this.lexer.state.top=!1,l.tokens=this.lexer.blockTokens(l.text,[]);let p=l.tokens[0];if(l.task&&((p==null?void 0:p.type)==="text"||(p==null?void 0:p.type)==="paragraph")){l.text=l.text.replace(this.rules.other.listReplaceTask,""),p.raw=p.raw.replace(this.rules.other.listReplaceTask,""),p.text=p.text.replace(this.rules.other.listReplaceTask,"");for(let h=this.lexer.inlineQueue.length-1;h>=0;h--)if(this.rules.other.listIsTask.test(this.lexer.inlineQueue[h].src)){this.lexer.inlineQueue[h].src=this.lexer.inlineQueue[h].src.replace(this.rules.other.listReplaceTask,"");break}let u=this.rules.other.listTaskCheckbox.exec(l.raw);if(u){let h={type:"checkbox",raw:u[0]+" ",checked:u[0]!=="[ ]"};l.checked=h.checked,r.loose?l.tokens[0]&&["paragraph","text"].includes(l.tokens[0].type)&&"tokens"in l.tokens[0]&&l.tokens[0].tokens?(l.tokens[0].raw=h.raw+l.tokens[0].raw,l.tokens[0].text=h.raw+l.tokens[0].text,l.tokens[0].tokens.unshift(h)):l.tokens.unshift({type:"paragraph",raw:h.raw,text:h.raw,tokens:[h]}):l.tokens.unshift(h)}}else l.task&&(l.task=!1);if(!r.loose){let u=l.tokens.filter(m=>m.type==="space"),h=u.length>0&&u.some(m=>this.rules.other.anyLine.test(m.raw));r.loose=h}}if(r.loose)for(let l of r.items){l.loose=!0;for(let p of l.tokens)p.type==="text"&&(p.type="paragraph")}return r}}html(t){let e=this.rules.block.html.exec(t);if(e){let s=xn(e[0]);return{type:"html",block:!0,raw:s,pre:e[1]==="pre"||e[1]==="script"||e[1]==="style",text:s}}}def(t){let e=this.rules.block.def.exec(t);if(e){let s=e[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal," "),n=e[2]?e[2].replace(this.rules.other.hrefBrackets,"$1").replace(this.rules.inline.anyPunctuation,"$1"):"",r=e[3]?e[3].substring(1,e[3].length-1).replace(this.rules.inline.anyPunctuation,"$1"):e[3];return{type:"def",tag:s,raw:_e(e[0],`
`),href:n,title:r}}}table(t){var a;let e=this.rules.block.table.exec(t);if(!e||!this.rules.other.tableDelimiter.test(e[2]))return;let s=yn(e[1]),n=e[2].replace(this.rules.other.tableAlignChars,"").split("|"),r=(a=e[3])!=null&&a.trim()?e[3].replace(this.rules.other.tableRowBlankLine,"").split(`
`):[],i={type:"table",raw:_e(e[0],`
`),header:[],align:[],rows:[]};if(s.length===n.length){for(let c of n)this.rules.other.tableAlignRight.test(c)?i.align.push("right"):this.rules.other.tableAlignCenter.test(c)?i.align.push("center"):this.rules.other.tableAlignLeft.test(c)?i.align.push("left"):i.align.push(null);for(let c=0;c<s.length;c++)i.header.push({text:s[c],tokens:this.lexer.inline(s[c]),header:!0,align:i.align[c]});for(let c of r)i.rows.push(yn(c,i.header.length).map((l,p)=>({text:l,tokens:this.lexer.inline(l),header:!1,align:i.align[p]})));return i}}lheading(t){let e=this.rules.block.lheading.exec(t);if(e){let s=e[1].trim();return{type:"heading",raw:_e(e[0],`
`),depth:e[2].charAt(0)==="="?1:2,text:s,tokens:this.lexer.inline(s)}}}paragraph(t){let e=this.rules.block.paragraph.exec(t);if(e){let s=e[1].charAt(e[1].length-1)===`
`?e[1].slice(0,-1):e[1];return{type:"paragraph",raw:e[0],text:s,tokens:this.lexer.inline(s)}}}text(t){let e=this.rules.block.text.exec(t);if(e)return{type:"text",raw:e[0],text:e[0],tokens:this.lexer.inline(e[0])}}escape(t){let e=this.rules.inline.escape.exec(t);if(e)return{type:"escape",raw:e[0],text:e[1]}}tag(t){let e=this.rules.inline.tag.exec(t);if(e)return!this.lexer.state.inLink&&this.rules.other.startATag.test(e[0])?this.lexer.state.inLink=!0:this.lexer.state.inLink&&this.rules.other.endATag.test(e[0])&&(this.lexer.state.inLink=!1),!this.lexer.state.inRawBlock&&this.rules.other.startPreScriptTag.test(e[0])?this.lexer.state.inRawBlock=!0:this.lexer.state.inRawBlock&&this.rules.other.endPreScriptTag.test(e[0])&&(this.lexer.state.inRawBlock=!1),{type:"html",raw:e[0],inLink:this.lexer.state.inLink,inRawBlock:this.lexer.state.inRawBlock,block:!1,text:e[0]}}link(t){let e=this.rules.inline.link.exec(t);if(e){let s=e[2].trim();if(!this.options.pedantic&&this.rules.other.startAngleBracket.test(s)){if(!this.rules.other.endAngleBracket.test(s))return;let i=_e(s.slice(0,-1),"\\");if((s.length-i.length)%2===0)return}else{let i=Mo(e[2],"()");if(i===-2)return;if(i>-1){let a=(e[0].indexOf("!")===0?5:4)+e[1].length+i;e[2]=e[2].substring(0,i),e[0]=e[0].substring(0,a).trim(),e[3]=""}}let n=e[2],r="";if(this.options.pedantic){let i=this.rules.other.pedanticHrefTitle.exec(n);i&&(n=i[1],r=i[3])}else r=e[3]?e[3].slice(1,-1):"";return n=n.trim(),this.rules.other.startAngleBracket.test(n)&&(this.options.pedantic&&!this.rules.other.endAngleBracket.test(s)?n=n.slice(1):n=n.slice(1,-1)),wn(e,{href:n&&n.replace(this.rules.inline.anyPunctuation,"$1"),title:r&&r.replace(this.rules.inline.anyPunctuation,"$1")},e[0],this.lexer,this.rules)}}reflink(t,e){let s;if((s=this.rules.inline.reflink.exec(t))||(s=this.rules.inline.nolink.exec(t))){let n=(s[2]||s[1]).replace(this.rules.other.multipleSpaceGlobal," "),r=e[n.toLowerCase()];if(!r){let i=s[0].charAt(0);return{type:"text",raw:i,text:i}}return wn(s,r,s[0],this.lexer,this.rules)}}emStrong(t,e,s=""){let n=this.rules.inline.emStrongLDelim.exec(t);if(!(!n||!n[1]&&!n[2]&&!n[3]&&!n[4]||n[4]&&s.match(this.rules.other.unicodeAlphaNumeric))&&(!(n[1]||n[3])||!s||this.rules.inline.punctuation.exec(s))){let r=[...n[0]].length-1,i,a,c=r,l=0,p=n[0][0]==="*"?this.rules.inline.emStrongRDelimAst:this.rules.inline.emStrongRDelimUnd;for(p.lastIndex=0,e=e.slice(-1*t.length+r);(n=p.exec(e))!==null;){if(i=n[1]||n[2]||n[3]||n[4]||n[5]||n[6],!i)continue;if(a=[...i].length,n[3]||n[4]){c+=a;continue}else if((n[5]||n[6])&&r%3&&!((r+a)%3)){l+=a;continue}if(c-=a,c>0)continue;a=Math.min(a,a+c+l);let u=[...n[0]][0].length,h=t.slice(0,r+n.index+u+a);if(Math.min(r,a)%2){let R=h.slice(1,-1);return{type:"em",raw:h,text:R,tokens:this.lexer.inlineTokens(R)}}let m=h.slice(2,-2);return{type:"strong",raw:h,text:m,tokens:this.lexer.inlineTokens(m)}}}}codespan(t){let e=this.rules.inline.code.exec(t);if(e){let s=e[2].replace(this.rules.other.newLineCharGlobal," "),n=this.rules.other.nonSpaceChar.test(s),r=this.rules.other.startingSpaceChar.test(s)&&this.rules.other.endingSpaceChar.test(s);return n&&r&&(s=s.substring(1,s.length-1)),{type:"codespan",raw:e[0],text:s}}}br(t){let e=this.rules.inline.br.exec(t);if(e)return{type:"br",raw:e[0]}}del(t,e,s=""){let n=this.rules.inline.delLDelim.exec(t);if(n&&(!n[1]||!s||this.rules.inline.punctuation.exec(s))){let r=[...n[0]].length-1,i,a,c=r,l=this.rules.inline.delRDelim;for(l.lastIndex=0,e=e.slice(-1*t.length+r);(n=l.exec(e))!==null;){if(i=n[1]||n[2]||n[3]||n[4]||n[5]||n[6],!i||(a=[...i].length,a!==r))continue;if(n[3]||n[4]){c+=a;continue}if(c-=a,c>0)continue;a=Math.min(a,a+c);let p=[...n[0]][0].length,u=t.slice(0,r+n.index+p+a),h=u.slice(r,-r);return{type:"del",raw:u,text:h,tokens:this.lexer.inlineTokens(h)}}}}autolink(t){let e=this.rules.inline.autolink.exec(t);if(e){let s,n;return e[2]==="@"?(s=e[1],n="mailto:"+s):(s=e[1],n=s),{type:"link",raw:e[0],text:s,href:n,tokens:[{type:"text",raw:s,text:s}]}}}url(t){var s;let e;if(e=this.rules.inline.url.exec(t)){let n,r;if(e[2]==="@")n=e[0],r="mailto:"+n;else{let i;do i=e[0],e[0]=((s=this.rules.inline._backpedal.exec(e[0]))==null?void 0:s[0])??"";while(i!==e[0]);n=e[0],e[1]==="www."?r="http://"+e[0]:r=e[0]}return{type:"link",raw:e[0],text:n,href:r,tokens:[{type:"text",raw:n,text:n}]}}}inlineText(t){let e=this.rules.inline.text.exec(t);if(e){let s=this.lexer.state.inRawBlock;return{type:"text",raw:e[0],text:e[0],escaped:s}}}},de=class nr{constructor(e){O(this,"tokens");O(this,"options");O(this,"state");O(this,"inlineQueue");O(this,"tokenizer");this.tokens=[],this.tokens.links=Object.create(null),this.options=e||Be,this.options.tokenizer=this.options.tokenizer||new ls,this.tokenizer=this.options.tokenizer,this.tokenizer.options=this.options,this.tokenizer.lexer=this,this.inlineQueue=[],this.state={inLink:!1,inRawBlock:!1,top:!0};let s={other:Q,block:Kt.normal,inline:vt.normal};this.options.pedantic?(s.block=Kt.pedantic,s.inline=vt.pedantic):this.options.gfm&&(s.block=Kt.gfm,this.options.breaks?s.inline=vt.breaks:s.inline=vt.gfm),this.tokenizer.rules=s}static get rules(){return{block:Kt,inline:vt}}static lex(e,s){return new nr(s).lex(e)}static lexInline(e,s){return new nr(s).inlineTokens(e)}lex(e){e=e.replace(Q.carriageReturn,`
`),this.blockTokens(e,this.tokens);for(let s=0;s<this.inlineQueue.length;s++){let n=this.inlineQueue[s];this.inlineTokens(n.src,n.tokens)}return this.inlineQueue=[],this.tokens}blockTokens(e,s=[],n=!1){var i,a,c;this.tokenizer.lexer=this,this.options.pedantic&&(e=e.replace(Q.tabCharGlobal,"    ").replace(Q.spaceLine,""));let r=1/0;for(;e;){if(e.length<r)r=e.length;else{this.infiniteLoopError(e.charCodeAt(0));break}let l;if((a=(i=this.options.extensions)==null?void 0:i.block)!=null&&a.some(u=>(l=u.call({lexer:this},e,s))?(e=e.substring(l.raw.length),s.push(l),!0):!1))continue;if(l=this.tokenizer.space(e)){e=e.substring(l.raw.length);let u=s.at(-1);l.raw.length===1&&u!==void 0?u.raw+=`
`:s.push(l);continue}if(l=this.tokenizer.code(e)){e=e.substring(l.raw.length);let u=s.at(-1);(u==null?void 0:u.type)==="paragraph"||(u==null?void 0:u.type)==="text"?(u.raw+=(u.raw.endsWith(`
`)?"":`
`)+l.raw,u.text+=`
`+l.text,this.inlineQueue.at(-1).src=u.text):s.push(l);continue}if(l=this.tokenizer.fences(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.heading(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.hr(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.blockquote(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.list(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.html(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.def(e)){e=e.substring(l.raw.length);let u=s.at(-1);(u==null?void 0:u.type)==="paragraph"||(u==null?void 0:u.type)==="text"?(u.raw+=(u.raw.endsWith(`
`)?"":`
`)+l.raw,u.text+=`
`+l.raw,this.inlineQueue.at(-1).src=u.text):this.tokens.links[l.tag]||(this.tokens.links[l.tag]={href:l.href,title:l.title},s.push(l));continue}if(l=this.tokenizer.table(e)){e=e.substring(l.raw.length),s.push(l);continue}if(l=this.tokenizer.lheading(e)){e=e.substring(l.raw.length),s.push(l);continue}let p=e;if((c=this.options.extensions)!=null&&c.startBlock){let u=1/0,h=e.slice(1),m;this.options.extensions.startBlock.forEach(R=>{m=R.call({lexer:this},h),typeof m=="number"&&m>=0&&(u=Math.min(u,m))}),u<1/0&&u>=0&&(p=e.substring(0,u+1))}if(this.state.top&&(l=this.tokenizer.paragraph(p))){let u=s.at(-1);n&&(u==null?void 0:u.type)==="paragraph"?(u.raw+=(u.raw.endsWith(`
`)?"":`
`)+l.raw,u.text+=`
`+l.text,this.inlineQueue.pop(),this.inlineQueue.at(-1).src=u.text):s.push(l),n=p.length!==e.length,e=e.substring(l.raw.length);continue}if(l=this.tokenizer.text(e)){e=e.substring(l.raw.length);let u=s.at(-1);(u==null?void 0:u.type)==="text"?(u.raw+=(u.raw.endsWith(`
`)?"":`
`)+l.raw,u.text+=`
`+l.text,this.inlineQueue.pop(),this.inlineQueue.at(-1).src=u.text):s.push(l);continue}if(e){this.infiniteLoopError(e.charCodeAt(0));break}}return this.state.top=!0,s}inline(e,s=[]){return this.inlineQueue.push({src:e,tokens:s}),s}inlineTokens(e,s=[]){var p,u,h,m,R;this.tokenizer.lexer=this;let n=e,r=null;if(this.tokens.links){let g=Object.keys(this.tokens.links);if(g.length>0)for(;(r=this.tokenizer.rules.inline.reflinkSearch.exec(n))!==null;)g.includes(r[0].slice(r[0].lastIndexOf("[")+1,-1))&&(n=n.slice(0,r.index)+"["+"a".repeat(r[0].length-2)+"]"+n.slice(this.tokenizer.rules.inline.reflinkSearch.lastIndex))}for(;(r=this.tokenizer.rules.inline.anyPunctuation.exec(n))!==null;)n=n.slice(0,r.index)+"++"+n.slice(this.tokenizer.rules.inline.anyPunctuation.lastIndex);let i;for(;(r=this.tokenizer.rules.inline.blockSkip.exec(n))!==null;)i=r[2]?r[2].length:0,n=n.slice(0,r.index+i)+"["+"a".repeat(r[0].length-i-2)+"]"+n.slice(this.tokenizer.rules.inline.blockSkip.lastIndex);n=((u=(p=this.options.hooks)==null?void 0:p.emStrongMask)==null?void 0:u.call({lexer:this},n))??n;let a=!1,c="",l=1/0;for(;e;){if(e.length<l)l=e.length;else{this.infiniteLoopError(e.charCodeAt(0));break}a||(c=""),a=!1;let g;if((m=(h=this.options.extensions)==null?void 0:h.inline)!=null&&m.some(E=>(g=E.call({lexer:this},e,s))?(e=e.substring(g.raw.length),s.push(g),!0):!1))continue;if(g=this.tokenizer.escape(e)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.tag(e)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.link(e)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.reflink(e,this.tokens.links)){e=e.substring(g.raw.length);let E=s.at(-1);g.type==="text"&&(E==null?void 0:E.type)==="text"?(E.raw+=g.raw,E.text+=g.text):s.push(g);continue}if(g=this.tokenizer.emStrong(e,n,c)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.codespan(e)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.br(e)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.del(e,n,c)){e=e.substring(g.raw.length),s.push(g);continue}if(g=this.tokenizer.autolink(e)){e=e.substring(g.raw.length),s.push(g);continue}if(!this.state.inLink&&(g=this.tokenizer.url(e))){e=e.substring(g.raw.length),s.push(g);continue}let K=e;if((R=this.options.extensions)!=null&&R.startInline){let E=1/0,ie=e.slice(1),te;this.options.extensions.startInline.forEach(T=>{te=T.call({lexer:this},ie),typeof te=="number"&&te>=0&&(E=Math.min(E,te))}),E<1/0&&E>=0&&(K=e.substring(0,E+1))}if(g=this.tokenizer.inlineText(K)){e=e.substring(g.raw.length),g.raw.slice(-1)!=="_"&&(c=g.raw.slice(-1)),a=!0;let E=s.at(-1);(E==null?void 0:E.type)==="text"?(E.raw+=g.raw,E.text+=g.text):s.push(g);continue}if(e){this.infiniteLoopError(e.charCodeAt(0));break}}return s}infiniteLoopError(e){let s="Infinite loop on byte: "+e;if(this.options.silent)console.error(s);else throw new Error(s)}},cs=class{constructor(t){O(this,"options");O(this,"parser");this.options=t||Be}space(t){return""}code({text:t,lang:e,escaped:s}){var i;let n=(i=(e||"").match(Q.notSpaceStart))==null?void 0:i[0],r=t.replace(Q.endingNewline,"")+`
`;return n?'<pre><code class="language-'+ge(n)+'">'+(s?r:ge(r,!0))+`</code></pre>
`:"<pre><code>"+(s?r:ge(r,!0))+`</code></pre>
`}blockquote({tokens:t}){return`<blockquote>
${this.parser.parse(t)}</blockquote>
`}html({text:t}){return t}def(t){return""}heading({tokens:t,depth:e}){return`<h${e}>${this.parser.parseInline(t)}</h${e}>
`}hr(t){return`<hr>
`}list(t){let e=t.ordered,s=t.start,n="";for(let a=0;a<t.items.length;a++){let c=t.items[a];n+=this.listitem(c)}let r=e?"ol":"ul",i=e&&s!==1?' start="'+s+'"':"";return"<"+r+i+`>
`+n+"</"+r+`>
`}listitem(t){return`<li>${this.parser.parse(t.tokens)}</li>
`}checkbox({checked:t}){return"<input "+(t?'checked="" ':"")+'disabled="" type="checkbox"> '}paragraph({tokens:t}){return`<p>${this.parser.parseInline(t)}</p>
`}table(t){let e="",s="";for(let r=0;r<t.header.length;r++)s+=this.tablecell(t.header[r]);e+=this.tablerow({text:s});let n="";for(let r=0;r<t.rows.length;r++){let i=t.rows[r];s="";for(let a=0;a<i.length;a++)s+=this.tablecell(i[a]);n+=this.tablerow({text:s})}return n&&(n=`<tbody>${n}</tbody>`),`<table>
<thead>
`+e+`</thead>
`+n+`</table>
`}tablerow({text:t}){return`<tr>
${t}</tr>
`}tablecell(t){let e=this.parser.parseInline(t.tokens),s=t.header?"th":"td";return(t.align?`<${s} align="${t.align}">`:`<${s}>`)+e+`</${s}>
`}strong({tokens:t}){return`<strong>${this.parser.parseInline(t)}</strong>`}em({tokens:t}){return`<em>${this.parser.parseInline(t)}</em>`}codespan({text:t}){return`<code>${ge(t,!0)}</code>`}br(t){return"<br>"}del({tokens:t}){return`<del>${this.parser.parseInline(t)}</del>`}link({href:t,title:e,tokens:s}){let n=this.parser.parseInline(s),r=vn(t);if(r===null)return n;t=r;let i='<a href="'+t+'"';return e&&(i+=' title="'+ge(e)+'"'),i+=">"+n+"</a>",i}image({href:t,title:e,text:s,tokens:n}){n&&(s=this.parser.parseInline(n,this.parser.textRenderer));let r=vn(t);if(r===null)return ge(s);t=r;let i=`<img src="${t}" alt="${ge(s)}"`;return e&&(i+=` title="${ge(e)}"`),i+=">",i}text(t){return"tokens"in t&&t.tokens?this.parser.parseInline(t.tokens):"escaped"in t&&t.escaped?t.text:ge(t.text)}},$r=class{strong({text:t}){return t}em({text:t}){return t}codespan({text:t}){return t}del({text:t}){return t}html({text:t}){return t}text({text:t}){return t}link({text:t}){return""+t}image({text:t}){return""+t}br(){return""}checkbox({raw:t}){return t}},ue=class ir{constructor(e){O(this,"options");O(this,"renderer");O(this,"textRenderer");this.options=e||Be,this.options.renderer=this.options.renderer||new cs,this.renderer=this.options.renderer,this.renderer.options=this.options,this.renderer.parser=this,this.textRenderer=new $r}static parse(e,s){return new ir(s).parse(e)}static parseInline(e,s){return new ir(s).parseInline(e)}parse(e){var n,r;this.renderer.parser=this;let s="";for(let i=0;i<e.length;i++){let a=e[i];if((r=(n=this.options.extensions)==null?void 0:n.renderers)!=null&&r[a.type]){let l=a,p=this.options.extensions.renderers[l.type].call({parser:this},l);if(p!==!1||!["space","hr","heading","code","table","blockquote","list","html","def","paragraph","text"].includes(l.type)){s+=p||"";continue}}let c=a;switch(c.type){case"space":{s+=this.renderer.space(c);break}case"hr":{s+=this.renderer.hr(c);break}case"heading":{s+=this.renderer.heading(c);break}case"code":{s+=this.renderer.code(c);break}case"table":{s+=this.renderer.table(c);break}case"blockquote":{s+=this.renderer.blockquote(c);break}case"list":{s+=this.renderer.list(c);break}case"checkbox":{s+=this.renderer.checkbox(c);break}case"html":{s+=this.renderer.html(c);break}case"def":{s+=this.renderer.def(c);break}case"paragraph":{s+=this.renderer.paragraph(c);break}case"text":{s+=this.renderer.text(c);break}default:{let l='Token with "'+c.type+'" type was not found.';if(this.options.silent)return console.error(l),"";throw new Error(l)}}}return s}parseInline(e,s=this.renderer){var r,i;this.renderer.parser=this;let n="";for(let a=0;a<e.length;a++){let c=e[a];if((i=(r=this.options.extensions)==null?void 0:r.renderers)!=null&&i[c.type]){let p=this.options.extensions.renderers[c.type].call({parser:this},c);if(p!==!1||!["escape","html","link","image","strong","em","codespan","br","del","text"].includes(c.type)){n+=p||"";continue}}let l=c;switch(l.type){case"escape":{n+=s.text(l);break}case"html":{n+=s.html(l);break}case"link":{n+=s.link(l);break}case"image":{n+=s.image(l);break}case"checkbox":{n+=s.checkbox(l);break}case"strong":{n+=s.strong(l);break}case"em":{n+=s.em(l);break}case"codespan":{n+=s.codespan(l);break}case"br":{n+=s.br(l);break}case"del":{n+=s.del(l);break}case"text":{n+=s.text(l);break}default:{let p='Token with "'+l.type+'" type was not found.';if(this.options.silent)return console.error(p),"";throw new Error(p)}}}return n}},Qt,xt=(Qt=class{constructor(t){O(this,"options");O(this,"block");this.options=t||Be}preprocess(t){return t}postprocess(t){return t}processAllTokens(t){return t}emStrongMask(t){return t}provideLexer(t=this.block){return t?de.lex:de.lexInline}provideParser(t=this.block){return t?ue.parse:ue.parseInline}},O(Qt,"passThroughHooks",new Set(["preprocess","postprocess","processAllTokens","emStrongMask"])),O(Qt,"passThroughHooksRespectAsync",new Set(["preprocess","postprocess","processAllTokens"])),Qt),Ho=class{constructor(...t){O(this,"defaults",mr());O(this,"options",this.setOptions);O(this,"parse",this.parseMarkdown(!0));O(this,"parseInline",this.parseMarkdown(!1));O(this,"Parser",ue);O(this,"Renderer",cs);O(this,"TextRenderer",$r);O(this,"Lexer",de);O(this,"Tokenizer",ls);O(this,"Hooks",xt);this.use(...t)}walkTokens(t,e){var n,r;let s=[];for(let i of t)switch(s=s.concat(e.call(this,i)),i.type){case"table":{let a=i;for(let c of a.header)s=s.concat(this.walkTokens(c.tokens,e));for(let c of a.rows)for(let l of c)s=s.concat(this.walkTokens(l.tokens,e));break}case"list":{let a=i;s=s.concat(this.walkTokens(a.items,e));break}default:{let a=i;(r=(n=this.defaults.extensions)==null?void 0:n.childTokens)!=null&&r[a.type]?this.defaults.extensions.childTokens[a.type].forEach(c=>{let l=a[c].flat(1/0);s=s.concat(this.walkTokens(l,e))}):a.tokens&&(s=s.concat(this.walkTokens(a.tokens,e)))}}return s}use(...t){let e=this.defaults.extensions||{renderers:{},childTokens:{}};return t.forEach(s=>{let n={...s};if(n.async=this.defaults.async||n.async||!1,s.extensions&&(s.extensions.forEach(r=>{if(!r.name)throw new Error("extension name required");if("renderer"in r){let i=e.renderers[r.name];i?e.renderers[r.name]=function(...a){let c=r.renderer.apply(this,a);return c===!1&&(c=i.apply(this,a)),c}:e.renderers[r.name]=r.renderer}if("tokenizer"in r){if(!r.level||r.level!=="block"&&r.level!=="inline")throw new Error("extension level must be 'block' or 'inline'");let i=e[r.level];i?i.unshift(r.tokenizer):e[r.level]=[r.tokenizer],r.start&&(r.level==="block"?e.startBlock?e.startBlock.push(r.start):e.startBlock=[r.start]:r.level==="inline"&&(e.startInline?e.startInline.push(r.start):e.startInline=[r.start]))}"childTokens"in r&&r.childTokens&&(e.childTokens[r.name]=r.childTokens)}),n.extensions=e),s.renderer){let r=this.defaults.renderer||new cs(this.defaults);for(let i in s.renderer){if(!(i in r))throw new Error(`renderer '${i}' does not exist`);if(["options","parser"].includes(i))continue;let a=i,c=s.renderer[a],l=r[a];r[a]=(...p)=>{let u=c.apply(r,p);return u===!1&&(u=l.apply(r,p)),u||""}}n.renderer=r}if(s.tokenizer){let r=this.defaults.tokenizer||new ls(this.defaults);for(let i in s.tokenizer){if(!(i in r))throw new Error(`tokenizer '${i}' does not exist`);if(["options","rules","lexer"].includes(i))continue;let a=i,c=s.tokenizer[a],l=r[a];r[a]=(...p)=>{let u=c.apply(r,p);return u===!1&&(u=l.apply(r,p)),u}}n.tokenizer=r}if(s.hooks){let r=this.defaults.hooks||new xt;for(let i in s.hooks){if(!(i in r))throw new Error(`hook '${i}' does not exist`);if(["options","block"].includes(i))continue;let a=i,c=s.hooks[a],l=r[a];xt.passThroughHooks.has(i)?r[a]=p=>{if(this.defaults.async&&xt.passThroughHooksRespectAsync.has(i))return(async()=>{let h=await c.call(r,p);return l.call(r,h)})();let u=c.call(r,p);return l.call(r,u)}:r[a]=(...p)=>{if(this.defaults.async)return(async()=>{let h=await c.apply(r,p);return h===!1&&(h=await l.apply(r,p)),h})();let u=c.apply(r,p);return u===!1&&(u=l.apply(r,p)),u}}n.hooks=r}if(s.walkTokens){let r=this.defaults.walkTokens,i=s.walkTokens;n.walkTokens=function(a){let c=[];return c.push(i.call(this,a)),r&&(c=c.concat(r.call(this,a))),c}}this.defaults={...this.defaults,...n}}),this}setOptions(t){return this.defaults={...this.defaults,...t},this}lexer(t,e){return de.lex(t,e??this.defaults)}parser(t,e){return ue.parse(t,e??this.defaults)}parseMarkdown(t){return(e,s)=>{let n={...s},r={...this.defaults,...n},i=this.onError(!!r.silent,!!r.async);if(this.defaults.async===!0&&n.async===!1)return i(new Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));if(typeof e>"u"||e===null)return i(new Error("marked(): input parameter is undefined or null"));if(typeof e!="string")return i(new Error("marked(): input parameter is of type "+Object.prototype.toString.call(e)+", string expected"));if(r.hooks&&(r.hooks.options=r,r.hooks.block=t),r.async)return(async()=>{let a=r.hooks?await r.hooks.preprocess(e):e,c=await(r.hooks?await r.hooks.provideLexer(t):t?de.lex:de.lexInline)(a,r),l=r.hooks?await r.hooks.processAllTokens(c):c;r.walkTokens&&await Promise.all(this.walkTokens(l,r.walkTokens));let p=await(r.hooks?await r.hooks.provideParser(t):t?ue.parse:ue.parseInline)(l,r);return r.hooks?await r.hooks.postprocess(p):p})().catch(i);try{r.hooks&&(e=r.hooks.preprocess(e));let a=(r.hooks?r.hooks.provideLexer(t):t?de.lex:de.lexInline)(e,r);r.hooks&&(a=r.hooks.processAllTokens(a)),r.walkTokens&&this.walkTokens(a,r.walkTokens);let c=(r.hooks?r.hooks.provideParser(t):t?ue.parse:ue.parseInline)(a,r);return r.hooks&&(c=r.hooks.postprocess(c)),c}catch(a){return i(a)}}}onError(t,e){return s=>{if(s.message+=`
Please report this to https://github.com/markedjs/marked.`,t){let n="<p>An error occurred:</p><pre>"+ge(s.message+"",!0)+"</pre>";return e?Promise.resolve(n):n}if(e)return Promise.reject(s);throw s}}},ze=new Ho;function C(t,e){return ze.parse(t,e)}C.options=C.setOptions=function(t){return ze.setOptions(t),C.defaults=ze.defaults,Xn(C.defaults),C};C.getDefaults=mr;C.defaults=Be;C.use=function(...t){return ze.use(...t),C.defaults=ze.defaults,Xn(C.defaults),C};C.walkTokens=function(t,e){return ze.walkTokens(t,e)};C.parseInline=ze.parseInline;C.Parser=ue;C.parser=ue.parse;C.Renderer=cs;C.TextRenderer=$r;C.Lexer=de;C.lexer=de.lex;C.Tokenizer=ls;C.Hooks=xt;C.parse=C;C.options;C.setOptions;C.use;C.walkTokens;C.parseInline;ue.parse;de.lex;/*! @license DOMPurify 3.4.9 | (c) Cure53 and other contributors | Released under the Apache license 2.0 and Mozilla Public License 2.0 | github.com/cure53/DOMPurify/blob/3.4.9/LICENSE */function kn(t,e){(e==null||e>t.length)&&(e=t.length);for(var s=0,n=Array(e);s<e;s++)n[s]=t[s];return n}function jo(t){if(Array.isArray(t))return t}function Fo(t,e){var s=t==null?null:typeof Symbol<"u"&&t[Symbol.iterator]||t["@@iterator"];if(s!=null){var n,r,i,a,c=[],l=!0,p=!1;try{if(i=(s=s.call(t)).next,e!==0)for(;!(l=(n=i.call(s)).done)&&(c.push(n.value),c.length!==e);l=!0);}catch(u){p=!0,r=u}finally{try{if(!l&&s.return!=null&&(a=s.return(),Object(a)!==a))return}finally{if(p)throw r}}return c}}function Bo(){throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Wo(t,e){return jo(t)||Fo(t,e)||qo(t,e)||Bo()}function qo(t,e){if(t){if(typeof t=="string")return kn(t,e);var s={}.toString.call(t).slice(8,-1);return s==="Object"&&t.constructor&&(s=t.constructor.name),s==="Map"||s==="Set"?Array.from(t):s==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(s)?kn(t,e):void 0}}const oi=Object.entries,_n=Object.setPrototypeOf,Go=Object.isFrozen,Vo=Object.getPrototypeOf,Yo=Object.getOwnPropertyDescriptor;let ee=Object.freeze,oe=Object.seal,et=Object.create,li=typeof Reflect<"u"&&Reflect,ar=li.apply,or=li.construct;ee||(ee=function(e){return e});oe||(oe=function(e){return e});ar||(ar=function(e,s){for(var n=arguments.length,r=new Array(n>2?n-2:0),i=2;i<n;i++)r[i-2]=arguments[i];return e.apply(s,r)});or||(or=function(e){for(var s=arguments.length,n=new Array(s>1?s-1:0),r=1;r<s;r++)n[r-1]=arguments[r];return new e(...n)});const ve=j(Array.prototype.forEach),Zo=j(Array.prototype.lastIndexOf),$n=j(Array.prototype.pop),Xe=j(Array.prototype.push),Ko=j(Array.prototype.splice),J=Array.isArray,wt=j(String.prototype.toLowerCase),qs=j(String.prototype.toString),Tn=j(String.prototype.match),Qe=j(String.prototype.replace),Sn=j(String.prototype.indexOf),Xo=j(String.prototype.trim),Qo=j(Number.prototype.toString),Jo=j(Boolean.prototype.toString),An=typeof BigInt>"u"?null:j(BigInt.prototype.toString),En=typeof Symbol>"u"?null:j(Symbol.prototype.toString),N=j(Object.prototype.hasOwnProperty),yt=j(Object.prototype.toString),Z=j(RegExp.prototype.test),Pe=el(TypeError);function j(t){return function(e){e instanceof RegExp&&(e.lastIndex=0);for(var s=arguments.length,n=new Array(s>1?s-1:0),r=1;r<s;r++)n[r-1]=arguments[r];return ar(t,e,n)}}function el(t){return function(){for(var e=arguments.length,s=new Array(e),n=0;n<e;n++)s[n]=arguments[n];return or(t,s)}}function _(t,e){let s=arguments.length>2&&arguments[2]!==void 0?arguments[2]:wt;if(_n&&_n(t,null),!J(e))return t;let n=e.length;for(;n--;){let r=e[n];if(typeof r=="string"){const i=s(r);i!==r&&(Go(e)||(e[n]=i),r=i)}t[r]=!0}return t}function tl(t){for(let e=0;e<t.length;e++)N(t,e)||(t[e]=null);return t}function X(t){const e=et(null);for(const n of oi(t)){var s=Wo(n,2);const r=s[0],i=s[1];N(t,r)&&(J(i)?e[r]=tl(i):i&&typeof i=="object"&&i.constructor===Object?e[r]=X(i):e[r]=i)}return e}function sl(t){switch(typeof t){case"string":return t;case"number":return Qo(t);case"boolean":return Jo(t);case"bigint":return An?An(t):"0";case"symbol":return En?En(t):"Symbol()";case"undefined":return yt(t);case"function":case"object":{if(t===null)return yt(t);const e=t,s=me(e,"toString");if(typeof s=="function"){const n=s(e);return typeof n=="string"?n:yt(n)}return yt(t)}default:return yt(t)}}function me(t,e){for(;t!==null;){const n=Yo(t,e);if(n){if(n.get)return j(n.get);if(typeof n.value=="function")return j(n.value)}t=Vo(t)}function s(){return null}return s}function rl(t){try{return Z(t,""),!0}catch{return!1}}const Rn=ee(["a","abbr","acronym","address","area","article","aside","audio","b","bdi","bdo","big","blink","blockquote","body","br","button","canvas","caption","center","cite","code","col","colgroup","content","data","datalist","dd","decorator","del","details","dfn","dialog","dir","div","dl","dt","element","em","fieldset","figcaption","figure","font","footer","form","h1","h2","h3","h4","h5","h6","head","header","hgroup","hr","html","i","img","input","ins","kbd","label","legend","li","main","map","mark","marquee","menu","menuitem","meter","nav","nobr","ol","optgroup","option","output","p","picture","pre","progress","q","rp","rt","ruby","s","samp","search","section","select","shadow","slot","small","source","spacer","span","strike","strong","style","sub","summary","sup","table","tbody","td","template","textarea","tfoot","th","thead","time","tr","track","tt","u","ul","var","video","wbr"]),Gs=ee(["svg","a","altglyph","altglyphdef","altglyphitem","animatecolor","animatemotion","animatetransform","circle","clippath","defs","desc","ellipse","enterkeyhint","exportparts","filter","font","g","glyph","glyphref","hkern","image","inputmode","line","lineargradient","marker","mask","metadata","mpath","part","path","pattern","polygon","polyline","radialgradient","rect","stop","style","switch","symbol","text","textpath","title","tref","tspan","view","vkern"]),Vs=ee(["feBlend","feColorMatrix","feComponentTransfer","feComposite","feConvolveMatrix","feDiffuseLighting","feDisplacementMap","feDistantLight","feDropShadow","feFlood","feFuncA","feFuncB","feFuncG","feFuncR","feGaussianBlur","feImage","feMerge","feMergeNode","feMorphology","feOffset","fePointLight","feSpecularLighting","feSpotLight","feTile","feTurbulence"]),nl=ee(["animate","color-profile","cursor","discard","font-face","font-face-format","font-face-name","font-face-src","font-face-uri","foreignobject","hatch","hatchpath","mesh","meshgradient","meshpatch","meshrow","missing-glyph","script","set","solidcolor","unknown","use"]),Ys=ee(["math","menclose","merror","mfenced","mfrac","mglyph","mi","mlabeledtr","mmultiscripts","mn","mo","mover","mpadded","mphantom","mroot","mrow","ms","mspace","msqrt","mstyle","msub","msup","msubsup","mtable","mtd","mtext","mtr","munder","munderover","mprescripts"]),il=ee(["maction","maligngroup","malignmark","mlongdiv","mscarries","mscarry","msgroup","mstack","msline","msrow","semantics","annotation","annotation-xml","mprescripts","none"]),Cn=ee(["#text"]),On=ee(["accept","action","align","alt","autocapitalize","autocomplete","autopictureinpicture","autoplay","background","bgcolor","border","capture","cellpadding","cellspacing","checked","cite","class","clear","color","cols","colspan","command","commandfor","controls","controlslist","coords","crossorigin","datetime","decoding","default","dir","disabled","disablepictureinpicture","disableremoteplayback","download","draggable","enctype","enterkeyhint","exportparts","face","for","headers","height","hidden","high","href","hreflang","id","inert","inputmode","integrity","ismap","kind","label","lang","list","loading","loop","low","max","maxlength","media","method","min","minlength","multiple","muted","name","nonce","noshade","novalidate","nowrap","open","optimum","part","pattern","placeholder","playsinline","popover","popovertarget","popovertargetaction","poster","preload","pubdate","radiogroup","readonly","rel","required","rev","reversed","role","rows","rowspan","spellcheck","scope","selected","shape","size","sizes","slot","span","srclang","start","src","srcset","step","style","summary","tabindex","title","translate","type","usemap","valign","value","width","wrap","xmlns"]),Zs=ee(["accent-height","accumulate","additive","alignment-baseline","amplitude","ascent","attributename","attributetype","azimuth","basefrequency","baseline-shift","begin","bias","by","class","clip","clippathunits","clip-path","clip-rule","color","color-interpolation","color-interpolation-filters","color-profile","color-rendering","cx","cy","d","dx","dy","diffuseconstant","direction","display","divisor","dur","edgemode","elevation","end","exponent","fill","fill-opacity","fill-rule","filter","filterunits","flood-color","flood-opacity","font-family","font-size","font-size-adjust","font-stretch","font-style","font-variant","font-weight","fx","fy","g1","g2","glyph-name","glyphref","gradientunits","gradienttransform","height","href","id","image-rendering","in","in2","intercept","k","k1","k2","k3","k4","kerning","keypoints","keysplines","keytimes","lang","lengthadjust","letter-spacing","kernelmatrix","kernelunitlength","lighting-color","local","marker-end","marker-mid","marker-start","markerheight","markerunits","markerwidth","maskcontentunits","maskunits","max","mask","mask-type","media","method","mode","min","name","numoctaves","offset","operator","opacity","order","orient","orientation","origin","overflow","paint-order","path","pathlength","patterncontentunits","patterntransform","patternunits","points","preservealpha","preserveaspectratio","primitiveunits","r","rx","ry","radius","refx","refy","repeatcount","repeatdur","restart","result","rotate","scale","seed","shape-rendering","slope","specularconstant","specularexponent","spreadmethod","startoffset","stddeviation","stitchtiles","stop-color","stop-opacity","stroke-dasharray","stroke-dashoffset","stroke-linecap","stroke-linejoin","stroke-miterlimit","stroke-opacity","stroke","stroke-width","style","surfacescale","systemlanguage","tabindex","tablevalues","targetx","targety","transform","transform-origin","text-anchor","text-decoration","text-rendering","textlength","type","u1","u2","unicode","values","viewbox","visibility","version","vert-adv-y","vert-origin-x","vert-origin-y","width","word-spacing","wrap","writing-mode","xchannelselector","ychannelselector","x","x1","x2","xmlns","y","y1","y2","z","zoomandpan"]),Pn=ee(["accent","accentunder","align","bevelled","close","columnalign","columnlines","columnspacing","columnspan","denomalign","depth","dir","display","displaystyle","encoding","fence","frame","height","href","id","largeop","length","linethickness","lquote","lspace","mathbackground","mathcolor","mathsize","mathvariant","maxsize","minsize","movablelimits","notation","numalign","open","rowalign","rowlines","rowspacing","rowspan","rspace","rquote","scriptlevel","scriptminsize","scriptsizemultiplier","selection","separator","separators","stretchy","subscriptshift","supscriptshift","symmetric","voffset","width","xmlns"]),Xt=ee(["xlink:href","xml:id","xlink:title","xml:space","xmlns:xlink"]),al=oe(/{{[\w\W]*|^[\w\W]*}}/g),ol=oe(/<%[\w\W]*|^[\w\W]*%>/g),ll=oe(/\${[\w\W]*/g),cl=oe(/^data-[\-\w.\u00B7-\uFFFF]+$/),dl=oe(/^aria-[\-\w]+$/),Dn=oe(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i),ul=oe(/^(?:\w+script|data):/i),pl=oe(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g),hl=oe(/^html$/i),fl=oe(/^[a-z][.\w]*(-[.\w]+)+$/i),fe={element:1,attribute:2,text:3,cdataSection:4,entityReference:5,entityNode:6,progressingInstruction:7,comment:8,document:9,documentType:10,documentFragment:11,notation:12},gl=function(){return typeof window>"u"?null:window},ml=function(e,s){if(typeof e!="object"||typeof e.createPolicy!="function")return null;let n=null;const r="data-tt-policy-suffix";s&&s.hasAttribute(r)&&(n=s.getAttribute(r));const i="dompurify"+(n?"#"+n:"");try{return e.createPolicy(i,{createHTML(a){return a},createScriptURL(a){return a}})}catch{return console.warn("TrustedTypes policy "+i+" could not be created."),null}},Nn=function(){return{afterSanitizeAttributes:[],afterSanitizeElements:[],afterSanitizeShadowDOM:[],beforeSanitizeAttributes:[],beforeSanitizeElements:[],beforeSanitizeShadowDOM:[],uponSanitizeAttribute:[],uponSanitizeElement:[],uponSanitizeShadowNode:[]}};function ci(){let t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:gl();const e=b=>ci(b);if(e.version="3.4.9",e.removed=[],!t||!t.document||t.document.nodeType!==fe.document||!t.Element)return e.isSupported=!1,e;let s=t.document;const n=s,r=n.currentScript;t.DocumentFragment;const i=t.HTMLTemplateElement,a=t.Node,c=t.Element,l=t.NodeFilter,p=t.NamedNodeMap;p===void 0&&(t.NamedNodeMap||t.MozNamedAttrMap),t.HTMLFormElement;const u=t.DOMParser,h=t.trustedTypes,m=c.prototype,R=me(m,"cloneNode"),g=me(m,"remove"),K=me(m,"nextSibling"),E=me(m,"childNodes"),ie=me(m,"parentNode"),te=me(m,"shadowRoot"),T=me(m,"attributes"),k=a&&a.prototype?me(a.prototype,"nodeType"):null,y=a&&a.prototype?me(a.prototype,"nodeName"):null;if(typeof i=="function"){const b=s.createElement("template");b.content&&b.content.ownerDocument&&(s=b.content.ownerDocument)}let S,ae="",dt,ut=!1,pt=0;const Ar=function(){if(pt>0)throw Pe('A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the "DOMPurify and Trusted Types" section of the README.')},We=function(o){Ar(),pt++;try{return S.createHTML(o)}finally{pt--}},ui=function(o){Ar(),pt++;try{return S.createScriptURL(o)}finally{pt--}},pi=function(){return ut||(dt=ml(h,r),ut=!0),dt},Mt=s,xs=Mt.implementation,Er=Mt.createNodeIterator,hi=Mt.createDocumentFragment,fi=Mt.getElementsByTagName,gi=n.importNode;let q=Nn();e.isSupported=typeof oi=="function"&&typeof ie=="function"&&xs&&xs.createHTMLDocument!==void 0;const zt=al,Ut=ol,Ht=ll,mi=cl,bi=dl,vi=ul,Rr=pl,yi=fl;let Cr=Dn,I=null;const ws=_({},[...Rn,...Gs,...Vs,...Ys,...Cn]);let L=null;const ks=_({},[...On,...Zs,...Pn,...Xt]);let M=Object.seal(et(null,{tagNameCheck:{writable:!0,configurable:!1,enumerable:!0,value:null},attributeNameCheck:{writable:!0,configurable:!1,enumerable:!0,value:null},allowCustomizedBuiltInElements:{writable:!0,configurable:!1,enumerable:!0,value:!1}})),ht=null,jt=null;const xe=Object.seal(et(null,{tagCheck:{writable:!0,configurable:!1,enumerable:!0,value:null},attributeCheck:{writable:!0,configurable:!1,enumerable:!0,value:null}}));let Or=!0,_s=!0,Pr=!1,Dr=!0,we=!1,ft=!0,Re=!1,$s=!1,Ts=!1,qe=!1,Ft=!1,Bt=!1,Nr=!0,Ir=!1;const Lr="user-content-";let Ss=!0,As=!1,Ge={},pe=null;const Es=_({},["annotation-xml","audio","colgroup","desc","foreignobject","head","iframe","math","mi","mn","mo","ms","mtext","noembed","noframes","noscript","plaintext","script","selectedcontent","style","svg","template","thead","title","video","xmp"]);let Mr=null;const zr=_({},["audio","video","img","source","image","track"]);let Rs=null;const Ur=_({},["alt","class","for","id","label","name","pattern","placeholder","role","summary","title","value","style","xmlns"]),Wt="http://www.w3.org/1998/Math/MathML",qt="http://www.w3.org/2000/svg",he="http://www.w3.org/1999/xhtml";let Ve=he,Cs=!1,Os=null;const xi=_({},[Wt,qt,he],qs);let Ps=_({},["mi","mo","mn","ms","mtext"]),Ds=_({},["annotation-xml"]);const wi=_({},["title","style","font","a","script"]);let gt=null;const ki=["application/xhtml+xml","text/html"],_i="text/html";let D=null,Ye=null;const $i=s.createElement("form"),Hr=function(o){return o instanceof RegExp||o instanceof Function},Ns=function(){let o=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{};if(Ye&&Ye===o)return;(!o||typeof o!="object")&&(o={}),o=X(o),gt=ki.indexOf(o.PARSER_MEDIA_TYPE)===-1?_i:o.PARSER_MEDIA_TYPE,D=gt==="application/xhtml+xml"?qs:wt,I=N(o,"ALLOWED_TAGS")&&J(o.ALLOWED_TAGS)?_({},o.ALLOWED_TAGS,D):ws,L=N(o,"ALLOWED_ATTR")&&J(o.ALLOWED_ATTR)?_({},o.ALLOWED_ATTR,D):ks,Os=N(o,"ALLOWED_NAMESPACES")&&J(o.ALLOWED_NAMESPACES)?_({},o.ALLOWED_NAMESPACES,qs):xi,Rs=N(o,"ADD_URI_SAFE_ATTR")&&J(o.ADD_URI_SAFE_ATTR)?_(X(Ur),o.ADD_URI_SAFE_ATTR,D):Ur,Mr=N(o,"ADD_DATA_URI_TAGS")&&J(o.ADD_DATA_URI_TAGS)?_(X(zr),o.ADD_DATA_URI_TAGS,D):zr,pe=N(o,"FORBID_CONTENTS")&&J(o.FORBID_CONTENTS)?_({},o.FORBID_CONTENTS,D):Es,ht=N(o,"FORBID_TAGS")&&J(o.FORBID_TAGS)?_({},o.FORBID_TAGS,D):X({}),jt=N(o,"FORBID_ATTR")&&J(o.FORBID_ATTR)?_({},o.FORBID_ATTR,D):X({}),Ge=N(o,"USE_PROFILES")?o.USE_PROFILES&&typeof o.USE_PROFILES=="object"?X(o.USE_PROFILES):o.USE_PROFILES:!1,Or=o.ALLOW_ARIA_ATTR!==!1,_s=o.ALLOW_DATA_ATTR!==!1,Pr=o.ALLOW_UNKNOWN_PROTOCOLS||!1,Dr=o.ALLOW_SELF_CLOSE_IN_ATTR!==!1,we=o.SAFE_FOR_TEMPLATES||!1,ft=o.SAFE_FOR_XML!==!1,Re=o.WHOLE_DOCUMENT||!1,qe=o.RETURN_DOM||!1,Ft=o.RETURN_DOM_FRAGMENT||!1,Bt=o.RETURN_TRUSTED_TYPE||!1,Ts=o.FORCE_BODY||!1,Nr=o.SANITIZE_DOM!==!1,Ir=o.SANITIZE_NAMED_PROPS||!1,Ss=o.KEEP_CONTENT!==!1,As=o.IN_PLACE||!1,Cr=rl(o.ALLOWED_URI_REGEXP)?o.ALLOWED_URI_REGEXP:Dn,Ve=typeof o.NAMESPACE=="string"?o.NAMESPACE:he,Ps=N(o,"MATHML_TEXT_INTEGRATION_POINTS")&&o.MATHML_TEXT_INTEGRATION_POINTS&&typeof o.MATHML_TEXT_INTEGRATION_POINTS=="object"?X(o.MATHML_TEXT_INTEGRATION_POINTS):_({},["mi","mo","mn","ms","mtext"]),Ds=N(o,"HTML_INTEGRATION_POINTS")&&o.HTML_INTEGRATION_POINTS&&typeof o.HTML_INTEGRATION_POINTS=="object"?X(o.HTML_INTEGRATION_POINTS):_({},["annotation-xml"]);const d=N(o,"CUSTOM_ELEMENT_HANDLING")&&o.CUSTOM_ELEMENT_HANDLING&&typeof o.CUSTOM_ELEMENT_HANDLING=="object"?X(o.CUSTOM_ELEMENT_HANDLING):et(null);if(M=et(null),N(d,"tagNameCheck")&&Hr(d.tagNameCheck)&&(M.tagNameCheck=d.tagNameCheck),N(d,"attributeNameCheck")&&Hr(d.attributeNameCheck)&&(M.attributeNameCheck=d.attributeNameCheck),N(d,"allowCustomizedBuiltInElements")&&typeof d.allowCustomizedBuiltInElements=="boolean"&&(M.allowCustomizedBuiltInElements=d.allowCustomizedBuiltInElements),we&&(_s=!1),Ft&&(qe=!0),Ge&&(I=_({},Cn),L=et(null),Ge.html===!0&&(_(I,Rn),_(L,On)),Ge.svg===!0&&(_(I,Gs),_(L,Zs),_(L,Xt)),Ge.svgFilters===!0&&(_(I,Vs),_(L,Zs),_(L,Xt)),Ge.mathMl===!0&&(_(I,Ys),_(L,Pn),_(L,Xt))),xe.tagCheck=null,xe.attributeCheck=null,N(o,"ADD_TAGS")&&(typeof o.ADD_TAGS=="function"?xe.tagCheck=o.ADD_TAGS:J(o.ADD_TAGS)&&(I===ws&&(I=X(I)),_(I,o.ADD_TAGS,D))),N(o,"ADD_ATTR")&&(typeof o.ADD_ATTR=="function"?xe.attributeCheck=o.ADD_ATTR:J(o.ADD_ATTR)&&(L===ks&&(L=X(L)),_(L,o.ADD_ATTR,D))),N(o,"ADD_URI_SAFE_ATTR")&&J(o.ADD_URI_SAFE_ATTR)&&_(Rs,o.ADD_URI_SAFE_ATTR,D),N(o,"FORBID_CONTENTS")&&J(o.FORBID_CONTENTS)&&(pe===Es&&(pe=X(pe)),_(pe,o.FORBID_CONTENTS,D)),N(o,"ADD_FORBID_CONTENTS")&&J(o.ADD_FORBID_CONTENTS)&&(pe===Es&&(pe=X(pe)),_(pe,o.ADD_FORBID_CONTENTS,D)),Ss&&(I["#text"]=!0),Re&&_(I,["html","head","body"]),I.table&&(_(I,["tbody"]),delete ht.tbody),o.TRUSTED_TYPES_POLICY){if(typeof o.TRUSTED_TYPES_POLICY.createHTML!="function")throw Pe('TRUSTED_TYPES_POLICY configuration option must provide a "createHTML" hook.');if(typeof o.TRUSTED_TYPES_POLICY.createScriptURL!="function")throw Pe('TRUSTED_TYPES_POLICY configuration option must provide a "createScriptURL" hook.');const f=S;S=o.TRUSTED_TYPES_POLICY;try{ae=We("")}catch(x){throw S=f,x}}else o.TRUSTED_TYPES_POLICY===null?(S=void 0,ae=""):(S===void 0&&(S=pi()),S&&typeof ae=="string"&&(ae=We("")));(q.uponSanitizeElement.length>0||q.uponSanitizeAttribute.length>0)&&I===ws&&(I=X(I)),q.uponSanitizeAttribute.length>0&&L===ks&&(L=X(L)),ee&&ee(o),Ye=o},jr=_({},[...Gs,...Vs,...nl]),Fr=_({},[...Ys,...il]),Ti=function(o){let d=ie(o);(!d||!d.tagName)&&(d={namespaceURI:Ve,tagName:"template"});const f=wt(o.tagName),x=wt(d.tagName);return Os[o.namespaceURI]?o.namespaceURI===qt?d.namespaceURI===he?f==="svg":d.namespaceURI===Wt?f==="svg"&&(x==="annotation-xml"||Ps[x]):!!jr[f]:o.namespaceURI===Wt?d.namespaceURI===he?f==="math":d.namespaceURI===qt?f==="math"&&Ds[x]:!!Fr[f]:o.namespaceURI===he?d.namespaceURI===qt&&!Ds[x]||d.namespaceURI===Wt&&!Ps[x]?!1:!Fr[f]&&(wi[f]||!jr[f]):!!(gt==="application/xhtml+xml"&&Os[o.namespaceURI]):!1},ce=function(o){Xe(e.removed,{element:o});try{ie(o).removeChild(o)}catch{if(g(o),!ie(o))throw Pe("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place")}},Br=function(o){const d=E?E(o):o.childNodes;if(d){const x=[];ve(d,w=>{Xe(x,w)}),ve(x,w=>{try{g(w)}catch{}})}const f=T?T(o):null;if(f)for(let x=f.length-1;x>=0;--x){const w=f[x],$=w&&w.name;if(typeof $=="string")try{o.removeAttribute($)}catch{}}},Ce=function(o,d){try{Xe(e.removed,{attribute:d.getAttributeNode(o),from:d})}catch{Xe(e.removed,{attribute:null,from:d})}if(d.removeAttribute(o),o==="is")if(qe||Ft)try{ce(d)}catch{}else try{d.setAttribute(o,"")}catch{}},Si=function(o){const d=T?T(o):o.attributes;if(d)for(let f=d.length-1;f>=0;--f){const x=d[f],w=x&&x.name;if(!(typeof w!="string"||L[D(w)]))try{o.removeAttribute(w)}catch{}}},Ai=function(o){const d=[o];for(;d.length>0;){const f=d.pop();(k?k(f):f.nodeType)===fe.element&&Si(f);const w=E?E(f):f.childNodes;if(w)for(let $=w.length-1;$>=0;--$)d.push(w[$])}},Wr=function(o){let d=null,f=null;if(Ts)o="<remove></remove>"+o;else{const $=Tn(o,/^[\r\n\t ]+/);f=$&&$[0]}gt==="application/xhtml+xml"&&Ve===he&&(o='<html xmlns="http://www.w3.org/1999/xhtml"><head></head><body>'+o+"</body></html>");const x=S?We(o):o;if(Ve===he)try{d=new u().parseFromString(x,gt)}catch{}if(!d||!d.documentElement){d=xs.createDocument(Ve,"template",null);try{d.documentElement.innerHTML=Cs?ae:x}catch{}}const w=d.body||d.documentElement;return o&&f&&w.insertBefore(s.createTextNode(f),w.childNodes[0]||null),Ve===he?fi.call(d,Re?"html":"body")[0]:Re?d.documentElement:w},qr=function(o){return Er.call(o.ownerDocument||o,o,l.SHOW_ELEMENT|l.SHOW_COMMENT|l.SHOW_TEXT|l.SHOW_PROCESSING_INSTRUCTION|l.SHOW_CDATA_SECTION,null)},Is=function(o){var d,f;o.normalize();const x=Er.call(o.ownerDocument||o,o,l.SHOW_TEXT|l.SHOW_COMMENT|l.SHOW_CDATA_SECTION|l.SHOW_PROCESSING_INSTRUCTION,null);let w=x.nextNode();for(;w;){let F=w.data;ve([zt,Ut,Ht],P=>{F=Qe(F,P," ")}),w.data=F,w=x.nextNode()}const $=(d=(f=o.querySelectorAll)===null||f===void 0?void 0:f.call(o,"template"))!==null&&d!==void 0?d:[];ve(Array.from($),F=>{Ze(F.content)&&Is(F.content)})},Gt=function(o){const d=y?y(o):null;return typeof d!="string"||D(d)!=="form"?!1:typeof o.nodeName!="string"||typeof o.textContent!="string"||typeof o.removeChild!="function"||o.attributes!==T(o)||typeof o.removeAttribute!="function"||typeof o.setAttribute!="function"||typeof o.namespaceURI!="string"||typeof o.insertBefore!="function"||typeof o.hasChildNodes!="function"||o.nodeType!==k(o)||o.childNodes!==E(o)},Ze=function(o){if(!k||typeof o!="object"||o===null)return!1;try{return k(o)===fe.documentFragment}catch{return!1}},mt=function(o){if(!k||typeof o!="object"||o===null)return!1;try{return typeof k(o)=="number"}catch{return!1}};function be(b,o,d){ve(b,f=>{f.call(e,o,d,Ye)})}const Gr=function(o){let d=null;if(be(q.beforeSanitizeElements,o,null),Gt(o))return ce(o),!0;const f=D(y?y(o):o.nodeName);if(be(q.uponSanitizeElement,o,{tagName:f,allowedTags:I}),ft&&o.hasChildNodes()&&!mt(o.firstElementChild)&&Z(/<[/\w!]/g,o.innerHTML)&&Z(/<[/\w!]/g,o.textContent)||ft&&o.namespaceURI===he&&f==="style"&&mt(o.firstElementChild)||o.nodeType===fe.progressingInstruction||ft&&o.nodeType===fe.comment&&Z(/<[/\w]/g,o.data))return ce(o),!0;if(ht[f]||!(xe.tagCheck instanceof Function&&xe.tagCheck(f))&&!I[f]){if(!ht[f]&&Yr(f)&&(M.tagNameCheck instanceof RegExp&&Z(M.tagNameCheck,f)||M.tagNameCheck instanceof Function&&M.tagNameCheck(f)))return!1;if(Ss&&!pe[f]){const w=ie(o),$=E(o);if($&&w){const F=$.length;for(let P=F-1;P>=0;--P){const z=As?$[P]:R($[P],!0);w.insertBefore(z,K(o))}}}return ce(o),!0}return(k?k(o):o.nodeType)===fe.element&&!Ti(o)||(f==="noscript"||f==="noembed"||f==="noframes")&&Z(/<\/no(script|embed|frames)/i,o.innerHTML)?(ce(o),!0):(we&&o.nodeType===fe.text&&(d=o.textContent,ve([zt,Ut,Ht],w=>{d=Qe(d,w," ")}),o.textContent!==d&&(Xe(e.removed,{element:o.cloneNode()}),o.textContent=d)),be(q.afterSanitizeElements,o,null),!1)},Vr=function(o,d,f){if(jt[d]||Nr&&(d==="id"||d==="name")&&(f in s||f in $i))return!1;const x=L[d]||xe.attributeCheck instanceof Function&&xe.attributeCheck(d,o);if(!(_s&&!jt[d]&&Z(mi,d))){if(!(Or&&Z(bi,d))){if(!x||jt[d]){if(!(Yr(o)&&(M.tagNameCheck instanceof RegExp&&Z(M.tagNameCheck,o)||M.tagNameCheck instanceof Function&&M.tagNameCheck(o))&&(M.attributeNameCheck instanceof RegExp&&Z(M.attributeNameCheck,d)||M.attributeNameCheck instanceof Function&&M.attributeNameCheck(d,o))||d==="is"&&M.allowCustomizedBuiltInElements&&(M.tagNameCheck instanceof RegExp&&Z(M.tagNameCheck,f)||M.tagNameCheck instanceof Function&&M.tagNameCheck(f))))return!1}else if(!Rs[d]){if(!Z(Cr,Qe(f,Rr,""))){if(!((d==="src"||d==="xlink:href"||d==="href")&&o!=="script"&&Sn(f,"data:")===0&&Mr[o])){if(!(Pr&&!Z(vi,Qe(f,Rr,"")))){if(f)return!1}}}}}}return!0},Ei=_({},["annotation-xml","color-profile","font-face","font-face-format","font-face-name","font-face-src","font-face-uri","missing-glyph"]),Yr=function(o){return!Ei[wt(o)]&&Z(yi,o)},Zr=function(o){be(q.beforeSanitizeAttributes,o,null);const d=o.attributes;if(!d||Gt(o))return;const f={attrName:"",attrValue:"",keepAttr:!0,allowedAttributes:L,forceKeepAttr:void 0};let x=d.length;for(;x--;){const w=d[x],$=w.name,F=w.namespaceURI,P=w.value,z=D($),ke=P;let G=$==="value"?ke:Xo(ke);if(f.attrName=z,f.attrValue=G,f.keepAttr=!0,f.forceKeepAttr=void 0,be(q.uponSanitizeAttribute,o,f),G=f.attrValue,Ir&&(z==="id"||z==="name")&&Sn(G,Lr)!==0&&(Ce($,o),G=Lr+G),ft&&Z(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i,G)){Ce($,o);continue}if(z==="attributename"&&Tn(G,"href")){Ce($,o);continue}if(f.forceKeepAttr)continue;if(!f.keepAttr){Ce($,o);continue}if(!Dr&&Z(/\/>/i,G)){Ce($,o);continue}we&&ve([zt,Ut,Ht],Xr=>{G=Qe(G,Xr," ")});const Kr=D(o.nodeName);if(!Vr(Kr,z,G)){Ce($,o);continue}if(S&&typeof h=="object"&&typeof h.getAttributeType=="function"&&!F)switch(h.getAttributeType(Kr,z)){case"TrustedHTML":{G=We(G);break}case"TrustedScriptURL":{G=ui(G);break}}if(G!==ke)try{F?o.setAttributeNS(F,$,G):o.setAttribute($,G),Gt(o)?ce(o):$n(e.removed)}catch{Ce($,o)}}be(q.afterSanitizeAttributes,o,null)},Vt=function(o){let d=null;const f=qr(o);for(be(q.beforeSanitizeShadowDOM,o,null);d=f.nextNode();)if(be(q.uponSanitizeShadowNode,d,null),Gr(d),Zr(d),Ze(d.content)&&Vt(d.content),(k?k(d):d.nodeType)===fe.element){const w=te?te(d):d.shadowRoot;Ze(w)&&(Ls(w),Vt(w))}be(q.afterSanitizeShadowDOM,o,null)},Ls=function(o){const d=[{node:o,shadow:null}];for(;d.length>0;){const f=d.pop();if(f.shadow){Vt(f.shadow);continue}const x=f.node,$=(k?k(x):x.nodeType)===fe.element,F=E?E(x):x.childNodes;if(F)for(let P=F.length-1;P>=0;--P)d.push({node:F[P],shadow:null});if($){const P=y?y(x):null;if(typeof P=="string"&&D(P)==="template"){const z=x.content;Ze(z)&&d.push({node:z,shadow:null})}}if($){const P=te?te(x):x.shadowRoot;Ze(P)&&d.push({node:null,shadow:P},{node:P,shadow:null})}}};return e.sanitize=function(b){let o=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},d=null,f=null,x=null,w=null;if(Cs=!b,Cs&&(b="<!-->"),typeof b!="string"&&!mt(b)&&(b=sl(b),typeof b!="string"))throw Pe("dirty is not a string, aborting");if(!e.isSupported)return b;$s||Ns(o),e.removed=[];const $=As&&typeof b!="string"&&mt(b);if($){const z=y?y(b):b.nodeName;if(typeof z=="string"){const ke=D(z);if(!I[ke]||ht[ke])throw Pe("root node is forbidden and cannot be sanitized in-place")}if(Gt(b))throw Pe("root node is clobbered and cannot be sanitized in-place");try{Ls(b)}catch(ke){throw Br(b),ke}}else if(mt(b))d=Wr("<!---->"),f=d.ownerDocument.importNode(b,!0),f.nodeType===fe.element&&f.nodeName==="BODY"||f.nodeName==="HTML"?d=f:d.appendChild(f),Ls(f);else{if(!qe&&!we&&!Re&&b.indexOf("<")===-1)return S&&Bt?We(b):b;if(d=Wr(b),!d)return qe?null:Bt?ae:""}d&&Ts&&ce(d.firstChild);const F=qr($?b:d);try{for(;x=F.nextNode();)Gr(x),Zr(x),Ze(x.content)&&Vt(x.content)}catch(z){throw $&&Br(b),z}if($)return ve(e.removed,z=>{z.element&&Ai(z.element)}),we&&Is(b),b;if(qe){if(we&&Is(d),Ft)for(w=hi.call(d.ownerDocument);d.firstChild;)w.appendChild(d.firstChild);else w=d;return(L.shadowroot||L.shadowrootmode)&&(w=gi.call(n,w,!0)),w}let P=Re?d.outerHTML:d.innerHTML;return Re&&I["!doctype"]&&d.ownerDocument&&d.ownerDocument.doctype&&d.ownerDocument.doctype.name&&Z(hl,d.ownerDocument.doctype.name)&&(P="<!DOCTYPE "+d.ownerDocument.doctype.name+`>
`+P),we&&ve([zt,Ut,Ht],z=>{P=Qe(P,z," ")}),S&&Bt?We(P):P},e.setConfig=function(){let b=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{};Ns(b),$s=!0},e.clearConfig=function(){Ye=null,$s=!1,S=dt,ae=""},e.isValidAttribute=function(b,o,d){Ye||Ns({});const f=D(b),x=D(o);return Vr(f,x,d)},e.addHook=function(b,o){typeof o=="function"&&Xe(q[b],o)},e.removeHook=function(b,o){if(o!==void 0){const d=Zo(q[b],o);return d===-1?void 0:Ko(q[b],d,1)[0]}return $n(q[b])},e.removeHooks=function(b){q[b]=[]},e.removeAllHooks=function(){q=Nn()},e}var bl=ci(),vl=Object.defineProperty,yl=Object.getOwnPropertyDescriptor,di=(t,e,s,n)=>{for(var r=n>1?void 0:n?yl(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&vl(e,s,r),r};C.setOptions({breaks:!0,gfm:!0});function xl(t){return bl.sanitize(C.parse(t,{async:!1}))}let ds=class extends V{render(){const t=this.msg;if(t.role==="user")return v`
        <div class="bubble user">
          ${t.image?v`<img class="attached" src=${t.image} alt="attached" />`:""}${t.text}
        </div>
      `;const e=!t.streaming&&(t.model||t.latency)?v`<div class="badge">
            ${t.model??""}${t.latency?` · ${t.latency<1e3?`${t.latency}ms`:`${(t.latency/1e3).toFixed(1)}s`}`:""}
          </div>`:"";return v`
      <div class="bubble ai ${t.streaming?"streaming":""}">
        <div class="md">${Qa(xl(t.text))}</div>
        ${e}
      </div>
    `}};ds.styles=se`
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
  `;di([le({attribute:!1})],ds.prototype,"msg",2);ds=di([re("chat-message")],ds);var wl=Object.defineProperty,kl=Object.getOwnPropertyDescriptor,Tr=(t,e,s,n)=>{for(var r=n>1?void 0:n?kl(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&wl(e,s,r),r};const _l={model:"◇",route:"⇢",symbolic:"∑",oracle:"⚛",thinking:"…",tool_call:"⚙",tool_result:"✓",final:"●"};function $l(t){switch(t.t){case"route":return`routed: ${t.reason??""} → ${t.model??""}`;case"symbolic":return`verified by ${t.engine??"sympy"} (${t.kind}): ${t.result}`;case"oracle":return`${t.domain} oracle: ${t.result??t.element??""}`;case"tool_call":return`tool: ${t.tool}`;case"tool_result":return`result from ${t.tool}: ${String(t.result??"").slice(0,80)}`;case"model":return`model: ${t.model??"?"} (loop ${t.loop??1})`;case"thinking":return String(t.text??"").slice(0,100);default:return t.t}}let Rt=class extends V{constructor(){super(...arguments),this.steps=[],this.open=!0}render(){return this.steps.length?v`
      <div class="trail">
        <header @click=${()=>this.open=!this.open}>
          <span>${this.open?"▾":"▸"}</span>
          <span>reasoning · ${this.steps.length} step${this.steps.length>1?"s":""}</span>
        </header>
        ${this.open?v`<ul>
              ${this.steps.map(t=>v`
                  <li class=${t.t==="symbolic"||t.t==="oracle"?"verify":""}>
                    <span class="ic">${_l[t.t]??"·"}</span>
                    <span>${$l(t)}</span>
                  </li>
                `)}
            </ul>`:""}
      </div>
    `:v``}};Rt.styles=se`
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
  `;Tr([le({attribute:!1})],Rt.prototype,"steps",2);Tr([W()],Rt.prototype,"open",2);Rt=Tr([re("reasoning-trail")],Rt);var Tl=Object.defineProperty,Sl=Object.getOwnPropertyDescriptor,vs=(t,e,s,n)=>{for(var r=n>1?void 0:n?Sl(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Tl(e,s,r),r};const In=1280;async function Al(t){return new Promise(e=>{const s=new Image;s.onload=()=>{let{width:n,height:r}=s;if(Math.max(n,r)>In){const a=In/Math.max(n,r);n=Math.round(n*a),r=Math.round(r*a)}const i=document.createElement("canvas");i.width=n,i.height=r,i.getContext("2d").drawImage(s,0,0,n,r);try{e(i.toDataURL("image/jpeg",.85))}catch{e(t)}},s.onerror=()=>e(t),s.src=t})}let it=class extends V{constructor(){super(...arguments),this.image=null,this.dragging=!1,this.onPaste=t=>{var e;for(const s of((e=t.clipboardData)==null?void 0:e.items)??[])if(s.type.startsWith("image/")){const n=s.getAsFile();n&&this.stageImage(n);return}}}firstUpdated(){document.addEventListener("paste",this.onPaste)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("paste",this.onPaste)}async stageImage(t){const e=await new Promise(s=>{const n=new FileReader;n.onload=()=>s(n.result),n.readAsDataURL(t)});this.image=await Al(e)}async onDrop(t){var n,r;t.preventDefault(),this.dragging=!1;const e=(r=(n=t.dataTransfer)==null?void 0:n.files)==null?void 0:r[0];if(!e)return;if(e.type.startsWith("image/"))return void this.stageImage(e);B(`Ingesting ${e.name}…`,"info");const s=await fn(e);s.ok?B(`Absorbed ${s.source} (${s.chunks} chunks)`,"success"):B(`Ingest failed: ${s.error??"unknown"}`,"danger")}autoGrow(){this.ta.style.height="auto",this.ta.style.height=`${Math.min(this.ta.scrollHeight,180)}px`}fire(){const t=this.ta.value.trim();!t&&!this.image||(this.dispatchEvent(new CustomEvent("send",{detail:{text:t,image:this.image},bubbles:!0,composed:!0})),this.ta.value="",this.image=null,this.autoGrow())}onKey(t){t.key==="Enter"&&!t.shiftKey&&(t.preventDefault(),this.fire())}pickFile(t,e){const s=document.createElement("input");s.type="file",s.accept=t,s.onchange=()=>{var n;return((n=s.files)==null?void 0:n[0])&&e(s.files[0])},s.click()}render(){return v`
      ${this.image?v`<span class="chip">
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
          @click=${()=>this.pickFile(".pdf,.txt,.md,.py,.js,.ts,.json",async t=>{B(`Ingesting ${t.name}…`,"info");const e=await fn(t);e.ok?B(`Absorbed ${e.source} (${e.chunks} chunks)`,"success"):B(`Ingest failed: ${e.error??"unknown"}`,"danger")})}>📎</button>
        <textarea rows="1" placeholder="Message DEEP…"
          @input=${this.autoGrow} @keydown=${this.onKey}></textarea>
        <ds-button variant="primary" @click=${this.fire}>Send</ds-button>
      </div>
    `}};it.styles=se`
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
  `;vs([W()],it.prototype,"image",2);vs([W()],it.prototype,"dragging",2);vs([ps("textarea")],it.prototype,"ta",2);it=vs([re("chat-composer")],it);var El=Object.getOwnPropertyDescriptor,Rl=(t,e,s,n)=>{for(var r=n>1?void 0:n?El(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=a(r)||r);return r};let lr=class extends Vn(V){updated(){const t=this.renderRoot.querySelector(".scroll");t&&(t.scrollTop=t.scrollHeight)}render(){const t=ne.get(),e=ns.get();return v`
      <div class="scroll">
        ${t.length===0?v`<div class="empty">
              <h2>How can I help, Aryan?</h2>
              <p>Ask anything — drop an image for vision, or a document to absorb it.</p>
            </div>`:t.map(s=>v`<chat-message .msg=${s}></chat-message>`)}
        ${e.length&&(Te.get()||Ea.get())?v`<reasoning-trail .steps=${e}></reasoning-trail>`:""}
        ${Te.get()?v`<div class="thinking"><span></span><span></span><span></span></div>`:""}
      </div>
      <div class="composer-area">
        <chat-composer
          @send=${s=>Ra(s.detail.text,s.detail.image)}
        ></chat-composer>
      </div>
    `}};lr.styles=se`
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
  `;lr=Rl([re("deep-chat")],lr);var Cl=Object.defineProperty,Ol=Object.getOwnPropertyDescriptor,Nt=(t,e,s,n)=>{for(var r=n>1?void 0:n?Ol(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Cl(e,s,r),r};function Pl(t){const e=t.atomic_number;return e>=57&&e<=71?{row:9,col:3+(e-57)}:e>=89&&e<=103?{row:10,col:3+(e-89)}:t.group&&t.period?{row:t.period,col:t.group}:null}let Ue=class extends V{constructor(){super(...arguments),this.elements=[],this.detail=null,this.constants=[],this.formulas=[]}connectedCallback(){super.connectedCallback(),Na().then(t=>this.elements=t.elements).catch(()=>{}),La().then(t=>this.constants=t.constants).catch(()=>{}),Ma().then(t=>this.formulas=t.formulas).catch(()=>{})}async pick(t){const e=await Ia(t).catch(()=>null);e!=null&&e.ok&&e.element&&(this.detail=e.element)}renderDetail(){const t=this.detail;if(!t)return v`<span style="color:var(--ds-text-muted)">Select an element for verified data.</span>`;const e=(s,n)=>n==null?"":v`<div class="row"><span>${s}</span><b>${n}</b></div>`;return v`
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
    `}render(){return v`
      <ds-panel heading="Periodic table · ${this.elements.length} elements · curated data">
        <div class="grid">
          ${this.elements.map(t=>{const e=Pl(t);return e?v`
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
            ${this.constants.map(t=>v`<div class="row"><span>${t.name} (${t.symbol})</span><b>${t.value} ${t.unit}</b></div>`)}
          </div>
        </ds-panel>
        <ds-panel heading="Formula library · ancient → modern">
          <div class="list mono">
            ${this.formulas.map(t=>v`<div class="row"><span>${t.name} <span class="era">${t.era}</span></span><b>${t.formula}</b></div>`)}
          </div>
        </ds-panel>
      </div>
    `}};Ue.styles=se`
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
  `;Nt([W()],Ue.prototype,"elements",2);Nt([W()],Ue.prototype,"detail",2);Nt([W()],Ue.prototype,"constants",2);Nt([W()],Ue.prototype,"formulas",2);Ue=Nt([re("science-view")],Ue);var Dl=Object.defineProperty,Nl=Object.getOwnPropertyDescriptor,It=(t,e,s,n)=>{for(var r=n>1?void 0:n?Nl(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Dl(e,s,r),r};let He=class extends V{constructor(){super(...arguments),this.providers=null,this.security=null,this.kstats=null,this.docs=[]}connectedCallback(){super.connectedCallback(),this.refresh()}async refresh(){Zn().then(t=>this.providers=t).catch(()=>{}),fetch("/api/security/status").then(t=>t.json()).then(t=>this.security=t).catch(()=>{}),fetch("/api/knowledge/stats").then(t=>t.json()).then(t=>this.kstats=t).catch(()=>{}),za().then(t=>this.docs=t.documents).catch(()=>{})}render(){const t=this.providers,e=this.security,s=this.kstats;return v`
      <ds-panel heading="AI providers">
        ${t?t.providers.map(n=>v`
                <div class="row">
                  <span class="k"><span class="dot ${n.ok?"ok":"bad"}"></span>${n.provider}</span>
                  <span class=${n.ok?"muted":"danger-text"}>${n.detail}</span>
                </div>
              `):v`<span class="muted">loading…</span>`}
        <div slot="actions"><ds-button size="sm" @click=${()=>void this.refresh()}>refresh</ds-button></div>
      </ds-panel>

      <ds-panel heading="Network security">
        ${e?v`
              <div class="row"><span class="k">devices</span>
                <b>${e.summary.total} total · ${e.summary.trusted} trusted ·
                <span class=${e.summary.suspicious?"danger-text":""}>${e.summary.suspicious} suspicious</span></b></div>
              <div class="row"><span class="k">interface</span><b>${e.interface} · ${e.local_ip}</b></div>
              <div class="row"><span class="k">gateway</span><b>${e.gateway}</b></div>
              <div class="row"><span class="k">active connections</span><b>${e.active_connections}</b></div>
              <div class="row"><span class="k">listening ports</span>
                <span class="tags">${(e.listening_ports??[]).slice(0,10).map(n=>v`<span class="tag">${n}</span>`)}</span></div>
            `:v`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Knowledge graph">
        ${s?v`
              <div class="row"><span class="k">entities</span><b>${s.entities}</b></div>
              <div class="row"><span class="k">relationships</span><b>${s.relationships}</b></div>
              <div class="row"><span class="k">types</span>
                <span class="tags">${Object.entries(s.entity_types).map(([n,r])=>v`<span class="tag">${n} ${r}</span>`)}</span></div>
              <div class="row"><span class="k">most connected</span>
                <b>${(s.most_connected??[]).slice(0,3).map(n=>n.name).join(" · ")}</b></div>
            `:v`<span class="muted">loading…</span>`}
      </ds-panel>

      <ds-panel heading="Ingested documents">
        ${this.docs.length?this.docs.map(n=>v`<div class="row"><span class="k">${n.source}</span><b>${n.chunks} chunks</b></div>`):v`<span class="muted">No documents ingested yet — drop a file into the chat.</span>`}
      </ds-panel>
    `}};He.styles=se`
    :host {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: var(--ds-space-4);
      padding: var(--ds-space-5);
      max-width: 1100px;
      margin: 0 auto;
      align-content: start;
    }
    .row {
      display: flex; justify-content: space-between; align-items: center;
      gap: var(--ds-space-3); padding: var(--ds-space-2) 0;
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
    }
    .row:last-child { border-bottom: none; }
    .row .k { color: var(--ds-text-soft); }
    .row b { font-family: var(--ds-font-mono); font-weight: 500; }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
    .ok { background: var(--ds-success); box-shadow: 0 0 6px var(--ds-success); }
    .bad { background: var(--ds-danger); box-shadow: 0 0 6px var(--ds-danger); }
    .warn { color: var(--ds-warning); }
    .danger-text { color: var(--ds-danger); }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-xs); }
    .tags { display: flex; flex-wrap: wrap; gap: var(--ds-space-1); }
    .tag {
      padding: 1px 8px; border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-pill);
      font-size: var(--ds-text-xs); color: var(--ds-text-soft);
      font-family: var(--ds-font-mono);
    }
  `;It([W()],He.prototype,"providers",2);It([W()],He.prototype,"security",2);It([W()],He.prototype,"kstats",2);It([W()],He.prototype,"docs",2);He=It([re("ops-view")],He);var Il=Object.defineProperty,Ll=Object.getOwnPropertyDescriptor,ys=(t,e,s,n)=>{for(var r=n>1?void 0:n?Ll(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Il(e,s,r),r};const Ml=["researcher","writer","planner","analyst","coder"];let at=class extends V{constructor(){super(...arguments),this.tasks=[],this.role="planner"}connectedCallback(){super.connectedCallback(),this.poll(),this.timer=setInterval(()=>void this.poll(),4e3)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this.timer)}async poll(){try{const t=await(await fetch("/api/agents/tasks")).json();this.tasks=t.tasks??[]}catch{}}async launch(){const t=this.ta.value.trim();if(t)try{const e=await fetch("/api/agents/task",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({role:this.role,task:t})}),s=await e.json();e.ok?(B(`Agent launched (${this.role})`,"success"),this.ta.value="",this.poll()):B(`Launch failed: ${s.detail??e.status}`,"danger")}catch{B("Launch failed","danger")}}render(){return v`
      <ds-panel heading="Launch agent mission">
        <div class="launch">
          <div class="roles">
            ${Ml.map(t=>v`
                <button class="chip ${this.role===t?"on":""}" @click=${()=>this.role=t}>${t}</button>
              `)}
          </div>
          <textarea placeholder="Describe the mission… e.g. 'Plan a study schedule for my exams next month'"></textarea>
          <ds-button variant="primary" @click=${()=>void this.launch()}>Launch</ds-button>
        </div>
      </ds-panel>

      <ds-panel heading="Task board · ${this.tasks.length} task${this.tasks.length===1?"":"s"}">
        ${this.tasks.length?this.tasks.map(t=>v`
                <div class="task">
                  <div class="head">
                    <b>${t.role??"agent"}</b>
                    <span class="status ${String(t.status??"").toLowerCase()}">${t.status??"?"}${t.progress!=null?` · ${t.progress}`:""}</span>
                  </div>
                  <span class="desc">${t.task??""}</span>
                  ${t.result?v`<div class="result">${String(t.result).slice(0,600)}</div>`:""}
                </div>
              `):v`<span class="muted">No agent tasks yet. Launch one above — it runs in the background on the live system.</span>`}
      </ds-panel>
    `}};at.styles=se`
    :host { display: grid; gap: var(--ds-space-4); padding: var(--ds-space-5); max-width: 860px; margin: 0 auto; align-content: start; }
    .launch { display: grid; gap: var(--ds-space-3); }
    textarea {
      width: 100%; min-height: 64px; resize: vertical;
      background: var(--ds-surface-2); color: var(--ds-text);
      border: 1px solid var(--ds-border); border-radius: var(--ds-radius-sm);
      padding: var(--ds-space-3); font-family: var(--ds-font-sans); font-size: var(--ds-text-sm);
    }
    textarea:focus { outline: none; border-color: var(--ds-border-accent); }
    .roles { display: flex; gap: var(--ds-space-2); flex-wrap: wrap; align-items: center; }
    .chip {
      padding: 3px 12px; border-radius: var(--ds-radius-pill);
      border: 1px solid var(--ds-border); background: none;
      color: var(--ds-text-soft); font-size: var(--ds-text-xs); cursor: pointer;
      transition: all var(--ds-dur-fast) var(--ds-ease-out);
    }
    .chip.on { background: rgba(var(--ds-periwinkle-rgb), 0.16); border-color: var(--ds-border-accent); color: var(--ds-text); }
    .task {
      display: grid; gap: 4px;
      padding: var(--ds-space-3) 0;
      border-bottom: 1px solid var(--ds-border);
      font-size: var(--ds-text-sm);
    }
    .task:last-child { border-bottom: none; }
    .head { display: flex; justify-content: space-between; gap: var(--ds-space-3); }
    .status { font-family: var(--ds-font-mono); font-size: var(--ds-text-xs); }
    .status.running { color: var(--ds-info); }
    .status.done, .status.completed { color: var(--ds-success); }
    .status.failed, .status.error { color: var(--ds-danger); }
    .desc { color: var(--ds-text-soft); }
    .result { color: var(--ds-text-muted); font-size: var(--ds-text-xs); white-space: pre-wrap; max-height: 120px; overflow-y: auto; }
    .muted { color: var(--ds-text-muted); font-size: var(--ds-text-sm); }
  `;ys([W()],at.prototype,"tasks",2);ys([W()],at.prototype,"role",2);ys([ps("textarea")],at.prototype,"ta",2);at=ys([re("agents-view")],at);var zl=Object.defineProperty,Ul=Object.getOwnPropertyDescriptor,Lt=(t,e,s,n)=>{for(var r=n>1?void 0:n?Ul(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&zl(e,s,r),r};let je=class extends V{constructor(){super(...arguments),this.open=!1,this.q="",this.sel=0}show(){this.open=!0,this.q="",this.sel=0,requestAnimationFrame(()=>{var t;return(t=this.input)==null?void 0:t.focus()})}hide(){this.open=!1}toggle(){this.open?this.hide():this.show()}results(){return Ba(this.q)}run(t){this.hide(),t.run()}onKey(t){const e=this.results();t.key==="Escape"?this.hide():t.key==="ArrowDown"?(t.preventDefault(),this.sel=Math.min(this.sel+1,e.length-1)):t.key==="ArrowUp"?(t.preventDefault(),this.sel=Math.max(this.sel-1,0)):t.key==="Enter"&&e[this.sel]&&this.run(e[this.sel])}render(){if(!this.open)return v``;const t=this.results();return v`
      <div class="scrim" @click=${e=>{e.target===e.currentTarget&&this.hide()}}>
        <div class="box">
          <input
            placeholder="Type a command…"
            .value=${this.q}
            @input=${e=>{this.q=e.target.value,this.sel=0}}
            @keydown=${this.onKey}
          />
          ${t.length?v`<ul>
                ${t.map((e,s)=>v`
                    <li class=${s===this.sel?"sel":""}
                        @mouseenter=${()=>this.sel=s}
                        @click=${()=>this.run(e)}>
                      <span>${e.label}</span>
                      ${e.hint?v`<span class="hint">${e.hint}</span>`:""}
                    </li>
                  `)}
              </ul>`:v`<div class="none">No matching commands.</div>`}
        </div>
      </div>
    `}};je.styles=se`
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
  `;Lt([W()],je.prototype,"open",2);Lt([W()],je.prototype,"q",2);Lt([W()],je.prototype,"sel",2);Lt([ps("input")],je.prototype,"input",2);je=Lt([re("command-palette")],je);var Hl=Object.defineProperty,jl=Object.getOwnPropertyDescriptor,Sr=(t,e,s,n)=>{for(var r=n>1?void 0:n?jl(e,s):e,i=t.length-1,a;i>=0;i--)(a=t[i])&&(r=(n?a(e,s,r):a(r))||r);return n&&r&&Hl(e,s,r),r};let Ct=class extends Vn(V){constructor(){super(...arguments),this.route=location.hash.slice(1)||"home",this.status="—",this.onHash=()=>{this.route=location.hash.slice(1)||"home"},this.onGlobalKey=t=>{var e;(t.ctrlKey||t.metaKey)&&t.key.toLowerCase()==="k"&&(t.preventDefault(),(e=this.renderRoot.querySelector("command-palette"))==null||e.toggle())}}connectedCallback(){super.connectedCallback(),Pa(),Da().then(t=>this.status=t.deep).catch(()=>this.status="offline"),window.addEventListener("hashchange",this.onHash),window.addEventListener("keydown",this.onGlobalKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("hashchange",this.onHash),window.removeEventListener("keydown",this.onGlobalKey)}render(){const t=er.get();return v`
      <header>
        <span class="dot ${t==="open"?"open":""}"></span>
        <span class="logo">DEEP</span>
        <span class="spacer"></span>
        <nav>
          <a href="#home">chat</a>
          <a href="#science">science</a>
          <a href="#ops">ops</a>
          <a href="#agents">agents</a>
        </nav>
        <span class="meta">${this.status} · ${Yn.get()}</span>
        <span class="meta kbd" title="Command palette">⌘K</span>
      </header>
      <main>
        ${this.route==="gallery"?v`<ds-gallery></ds-gallery>`:this.route==="science"?v`<science-view></science-view>`:this.route==="ops"?v`<ops-view></ops-view>`:this.route==="agents"?v`<agents-view></agents-view>`:v`<deep-chat></deep-chat>`}
      </main>
      <command-palette></command-palette>
    `}};Ct.styles=se`
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
  `;Sr([W()],Ct.prototype,"route",2);Sr([W()],Ct.prototype,"status",2);Ct=Sr([re("deep-app")],Ct);
//# sourceMappingURL=index-BiBKqy7I.js.map
