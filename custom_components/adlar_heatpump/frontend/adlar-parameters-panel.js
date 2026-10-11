//#region node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: d, getOwnPropertyNames: ee, getOwnPropertySymbols: te, getPrototypeOf: ne } = Object, f = globalThis, p = f.trustedTypes, re = p ? p.emptyScript : "", ie = f.reactiveElementPolyfillSupport, m = (e, t) => e, h = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? re : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, g = (e, t) => !l(e, t), _ = {
	attribute: !0,
	type: String,
	converter: h,
	reflect: !1,
	useDefault: !1,
	hasChanged: g
};
Symbol.metadata ??= Symbol("metadata"), f.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var v = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = _) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = d(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? _;
	}
	static _$Ei() {
		if (this.hasOwnProperty(m("elementProperties"))) return;
		let e = ne(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(m("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(m("properties"))) {
			let e = this.properties, t = [...ee(e), ...te(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? h : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? h : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? g)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
v.elementStyles = [], v.shadowRootOptions = { mode: "open" }, v[m("elementProperties")] = /* @__PURE__ */ new Map(), v[m("finalized")] = /* @__PURE__ */ new Map(), ie?.({ ReactiveElement: v }), (f.reactiveElementVersions ??= []).push("2.1.2");
//#endregion
//#region node_modules/lit-html/lit-html.js
var y = globalThis, ae = (e) => e, b = y.trustedTypes, oe = b ? b.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, x = "$lit$", S = `lit$${Math.random().toFixed(9).slice(2)}$`, C = "?" + S, se = `<${C}>`, w = document, T = () => w.createComment(""), E = (e) => e === null || typeof e != "object" && typeof e != "function", D = Array.isArray, ce = (e) => D(e) || typeof e?.[Symbol.iterator] == "function", O = "[ 	\n\f\r]", k = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, A = /-->/g, j = />/g, M = RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), le = /'/g, ue = /"/g, N = /^(?:script|style|textarea|title)$/i, P = ((e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}))(1), F = Symbol.for("lit-noChange"), I = Symbol.for("lit-nothing"), L = /* @__PURE__ */ new WeakMap(), R = w.createTreeWalker(w, 129);
function z(e, t) {
	if (!D(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return oe === void 0 ? t : oe.createHTML(t);
}
var de = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = k;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === k ? c[1] === "!--" ? o = A : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = M) : (N.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = M) : o = j : o === M ? c[0] === ">" ? (o = i ?? k, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? M : c[3] === "\"" ? ue : le) : o === ue || o === le ? o = M : o === A || o === j ? o = k : (o = M, i = void 0);
		let d = o === M && e[t + 1].startsWith("/>") ? " " : "";
		a += o === k ? n + se : l >= 0 ? (r.push(s), n.slice(0, l) + x + n.slice(l) + S + d) : n + S + (l === -2 ? t : d);
	}
	return [z(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, B = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = de(t, n);
		if (this.el = e.createElement(l, r), R.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = R.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(x)) {
					let t = u[o++], n = i.getAttribute(e).split(S), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? pe : r[1] === "?" ? me : r[1] === "@" ? he : U
					}), i.removeAttribute(e);
				} else e.startsWith(S) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (N.test(i.tagName)) {
					let e = i.textContent.split(S), t = e.length - 1;
					if (t > 0) {
						i.textContent = b ? b.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], T()), R.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], T());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === C) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(S, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += S.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = w.createElement("template");
		return n.innerHTML = e, n;
	}
};
function V(e, t, n = e, r) {
	if (t === F) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = E(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = V(e, i._$AS(e, t.values), i, r)), t;
}
var fe = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? w).importNode(t, !0);
		R.currentNode = r;
		let i = R.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new H(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new ge(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = R.nextNode(), a++);
		}
		return R.currentNode = w, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, H = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = I, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = V(this, e, t), E(e) ? e === I || e == null || e === "" ? (this._$AH !== I && this._$AR(), this._$AH = I) : e !== this._$AH && e !== F && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? ce(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== I && E(this._$AH) ? this._$AA.nextSibling.data = e : this.T(w.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = B.createElement(z(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new fe(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = L.get(e.strings);
		return t === void 0 && L.set(e.strings, t = new B(e)), t;
	}
	k(t) {
		D(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(T()), this.O(T()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = ae(e).nextSibling;
			ae(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, U = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = I, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = I;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = V(this, e, t, 0), a = !E(e) || e !== this._$AH && e !== F, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = V(this, r[n + o], t, o), s === F && (s = this._$AH[o]), a ||= !E(s) || s !== this._$AH[o], s === I ? e = I : e !== I && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === I ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, pe = class extends U {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === I ? void 0 : e;
	}
}, me = class extends U {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== I);
	}
}, he = class extends U {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = V(this, e, t, 0) ?? I) === F) return;
		let n = this._$AH, r = e === I && n !== I || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== I && (n === I || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, ge = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		V(this, e);
	}
}, _e = y.litHtmlPolyfillSupport;
_e?.(B, H), (y.litHtmlVersions ??= []).push("3.3.3");
var ve = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new H(t.insertBefore(T(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, W = globalThis, G = class extends v {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = ve(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return F;
	}
};
G._$litElement$ = !0, G.finalized = !0, W.litElementHydrateSupport?.({ LitElement: G });
var ye = W.litElementPolyfillSupport;
ye?.({ LitElement: G }), (W.litElementVersions ??= []).push("4.2.2");
//#endregion
//#region src/texts.ts
var K = {
	title: "Heat pump parameters",
	heatPump: "Heat pump",
	loading: "Loading…",
	retry: "Try again",
	dismiss: "Dismiss",
	noEntries: "No heat pump is set up.",
	notLoaded: "This heat pump cannot be reached, so its parameters cannot be read or changed. The sensor and automation choices can still be changed.",
	pumpManual: "DC pump control is not on Auto. The pump now runs at the speed set by hand, whatever the heat pump needs: a stopped or slow pump with a running compressor can freeze the plate heat exchanger. Set DC pump control back to Auto when you are done.",
	search: "Search code, name or description",
	differing: "Differs from baseline",
	baselineReference: "Baseline: the HHI reference defaults.",
	baselineSetOn: (e) => `Baseline: set on ${e}.`,
	setBaseline: "Set baseline",
	settingBaseline: "Reading every parameter…",
	setBaselineTitle: "Set the baseline?",
	setBaselineBody: "The current value of every parameter becomes the baseline and replaces the one in use. Every parameter is read from the heat pump, which takes several seconds.",
	baselineSet: "The baseline is set to the current values.",
	recommended: "Recommended sensors",
	recommendedHint: "Stage the recommended set of parameters as the sensors",
	export: "Export",
	exporting: "Reading every parameter…",
	exported: (e) => `Exported to ${e}.`,
	noMatches: "No parameter matches.",
	parameters: (e) => e === 1 ? "1 parameter" : `${e} parameters`,
	shownOf: (e, t) => `${e} of ${t}`,
	unknownDiff: (e) => `, ${e} not read`,
	reading: "Reading from the heat pump…",
	readAgain: "Read again",
	readFailed: (e) => `The heat pump did not answer: ${e}`,
	noRows: "No parameter of this group matches.",
	noValue: "—",
	range: (e) => `Range ${e}`,
	options: (e) => `Options: ${e}`,
	rangeOf: (e, t) => `${e} to ${t}`,
	baseline: (e) => `Baseline ${e}`,
	differs: "differs",
	readOnly: "Read-only",
	edit: "Edit",
	save: "Save",
	cancel: "Cancel",
	newValue: (e) => `New value of ${e}`,
	writing: "Writing…",
	written: (e) => `Written. The heat pump now reports ${e}.`,
	notWritten: (e) => `Not written: ${e}`,
	errNumber: "Enter a number.",
	errOption: "Choose one of the options.",
	errRange: (e) => `Must be within ${e}.`,
	errStep: (e) => `Must be a multiple of ${e}.`,
	confirmWriteTitle: "Write this parameter?",
	confirmWrite: "Write",
	oldValue: "Current value",
	newValueShort: "New value",
	rangeLabel: "Range",
	warnings: {
		factory: "Factory setting: change it only on the manufacturer's advice. A wrong value can damage the heat pump.",
		protection: "This parameter is part of the heat pump's protection. A wrong value can switch off a safeguard and damage the unit.",
		dc_pump: "Manual DC pump control stays on until it is set back to Auto. A stopped or slow pump with a running compressor can freeze the plate heat exchanger."
	},
	sensor: "Sensor",
	sensorHint: "Show this parameter as a sensor entity",
	automation: "Allow automations",
	automationHint: "The adlar_heatpump.set_parameter service may write this parameter",
	confirmAutomationTitle: "Allow automations to write this parameter?",
	confirmAutomationBody: "The adlar_heatpump.set_parameter service may then write it, without anyone confirming the value.",
	confirmAutomation: "Allow",
	staged: (e) => e === 1 ? "1 change staged." : `${e} changes staged.`,
	applyHint: "Applying reloads the heat pump's entities.",
	apply: "Apply",
	applying: "Applying…",
	discard: "Discard",
	applied: "The choices are stored and the heat pump's entities were reloaded.",
	stagedFirst: "Apply or discard the staged changes first"
}, q = (e) => e.code ? `${e.code} ${e.name}` : e.name, J = (e) => String(Number(e.toFixed(4)));
function Y(e, t) {
	return t === null ? K.noValue : e.options ? e.options.find((e) => e.value === t)?.label ?? J(t) : e.unit ? `${J(t)} ${e.unit}` : J(t);
}
function X(e) {
	return e.options ? e.options.map((e) => e.label).join(", ") : e.min === null || e.max === null ? null : K.rangeOf(J(e.min), Y(e, e.max));
}
var Z = (e) => e.baseline !== null && e.value !== null && e.baseline !== e.value;
function be(e, t) {
	let n = `${e.code ?? ""} ${e.name} ${e.description ?? ""}`.toLowerCase();
	return t.toLowerCase().split(/\s+/).every((e) => n.includes(e));
}
function xe(e, t, n) {
	let r = t.trim() !== "" || n;
	return e.map((e) => {
		let r = e.parameters.filter((e) => be(e, t));
		return {
			group: e,
			rows: n ? r.filter(Z) : r,
			unknown: n ? r.filter((e) => e.baseline !== null && e.value === null).length : 0
		};
	}).filter((e) => !r || e.rows.length > 0 || e.unknown > 0);
}
function Se(e, t) {
	return e.map((e) => ({
		...e,
		parameters: e.parameters.map((e) => e.key in t ? {
			...e,
			value: t[e.key]
		} : e)
	}));
}
function Ce(e, t) {
	let n = Number(t);
	return t.trim() === "" || !Number.isFinite(n) ? { error: K.errNumber } : e.options ? e.options.some((e) => e.value === n) ? { value: n } : { error: K.errOption } : e.min !== null && n < e.min || e.max !== null && n > e.max ? { error: K.errRange(X(e) ?? "") } : e.step && Math.abs(n / e.step - Math.round(n / e.step)) > 1e-6 ? { error: K.errStep(J(e.step)) } : { value: n };
}
function Q(e) {
	let t = e.flatMap((e) => e.parameters);
	return {
		sensors: new Set(t.filter((e) => e.sensor).map((e) => e.key)),
		automations: new Set(t.filter((e) => e.automation).map((e) => e.key))
	};
}
var we = (e) => e.warning === "factory" || e.warning === "dc_pump";
function Te(e, t, n) {
	let r = new Set(e);
	return n ? r.add(t) : r.delete(t), r;
}
var Ee = (e, t) => [...e].filter((e) => !t.has(e)).length + [...t].filter((t) => !e.has(t)).length, De = (e, t) => Ee(e.sensors, t.sensors) + Ee(e.automations, t.automations), Oe = (e) => ({
	sensors: [...e.sensors].sort(),
	automations: [...e.automations].sort()
});
function ke(e, t, n) {
	return {
		name: `${e.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}-parameters-${t.toISOString().slice(0, 10)}.json`,
		content: JSON.stringify({
			title: e,
			exported_at: t.toISOString(),
			parameters: n
		}, null, 2)
	};
}
//#endregion
//#region src/row.ts
var Ae = (e) => e.target.value;
function je(e, t, n) {
	let r = Ce(e, t), i = "value" in r && r.value === e.value;
	return P`<form class="editor" novalidate @submit=${(t) => {
		t.preventDefault(), "value" in r && !i && n.onSave(e, r.value);
	}}>
      ${e.options ? P`<select aria-label=${K.newValue(q(e))} @change=${(e) => n.onInput(Ae(e))}>
            ${e.options.map((e) => P`<option value=${e.value} ?selected=${String(e.value) === t}>${e.label}</option>`)}
          </select>` : P`<input
              type="number"
              inputmode="decimal"
              aria-label=${K.newValue(q(e))}
              min=${e.min ?? I}
              max=${e.max ?? I}
              step=${e.step ?? I}
              .value=${t}
              @input=${(e) => n.onInput(Ae(e))}
            />${e.unit ? P`<span class="unit">${e.unit}</span>` : I}`}
      <button class="btn primary" type="submit" ?disabled=${"error" in r || i}>${K.save}</button>
      <button class="btn" type="button" @click=${() => n.onEdit(null)}>${K.cancel}</button>
    </form>
    ${"error" in r ? P`<div class="result error" role="alert">${r.error}</div>` : I}`;
}
function Me(e, t) {
	return P`<div class="current">
    <span class="number">${t.writing === e.key ? K.writing : Y(e, e.value)}</span>
    ${e.can_edit ? e.value === null ? I : P`<button class="btn" aria-label="${K.edit} ${q(e)}" ?disabled=${!t.idle} @click=${() => t.onEdit(e)}>
            ${K.edit}
          </button>` : P`<span class="tag">${K.readOnly}</span>`}
  </div>`;
}
function Ne(e, t, n, r, i, a) {
	let o = a.staged[t].has(e.key);
	return P`<label class=${o === n ? "" : "staged"} title=${i}>
    <input type="checkbox" .checked=${o} @change=${(n) => {
		let r = n.target, i = r.checked;
		r.checked = o, a.onChoice(e, t, i);
	}} />${r}
  </label>`;
}
function Pe(e, t) {
	let n = X(e);
	return P`<div class="row ${Z(e) ? "differs" : ""}">
    <div class="what">
      ${e.code ? P`<span class="code">${e.code}</span>` : I}
      <div>
        <div class="name">${e.name}</div>
        ${e.description ? P`<div class="secondary">${e.description}</div>` : I}
      </div>
    </div>
    <div class="value">
      ${t.edit?.key === e.key ? je(e, t.edit.input, t) : Me(e, t)}
      ${n ? P`<div class="secondary">${e.options ? K.options(n) : K.range(n)}</div>` : I}
      ${Z(e) ? P`<div class="baseline">${K.baseline(Y(e, e.baseline))} <span class="pill">${K.differs}</span></div>` : I}
      ${t.result?.key === e.key ? P`<div class="result ${t.result.ok ? "ok" : "error"}" role="status">${t.result.text}</div>` : I}
    </div>
    <div class="choices">
      ${Ne(e, "sensors", e.sensor, K.sensor, K.sensorHint, t)}
      ${e.can_edit ? Ne(e, "automations", e.automation, K.automation, K.automationHint, t) : I}
    </div>
  </div>`;
}
//#endregion
//#region src/styles.ts
var Fe = o`
  :host {
    display: block;
    height: 100dvh;
    color: var(--primary-text-color);
    background: var(--primary-background-color);
  }
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    container-type: inline-size;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    box-sizing: border-box;
    height: var(--header-height, 56px);
    padding: 0 12px;
    flex: none;
    color: var(--app-header-text-color, var(--primary-text-color));
    background: var(--app-header-background-color, var(--primary-color));
    border-bottom: var(--app-header-border-bottom, none);
  }
  h1 {
    flex: 1;
    min-width: 0;
    margin: 0 4px;
    font-size: 20px;
    font-weight: 400;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .header select {
    flex: 0 1 auto;
    min-width: 0;
    max-width: 50%;
  }
  @container (max-width: 520px) {
    /* The selector gets a line of its own under the title */
    .header {
      flex-wrap: wrap;
      height: auto;
      min-height: var(--header-height, 56px);
    }
    .header select {
      flex: 1 1 100%;
      max-width: none;
      margin-bottom: 8px;
    }
  }
  .content {
    flex: 1;
    overflow-y: auto;
  }
  .inner,
  .pinned {
    box-sizing: border-box;
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .pinned {
    flex: none;
    padding-bottom: 12px;
  }

  /* Controls */
  button,
  input,
  select {
    font: inherit;
    color: var(--primary-text-color);
  }
  .btn {
    height: 36px;
    padding: 0 12px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: transparent;
    color: var(--primary-color);
    font-weight: 500;
    white-space: nowrap;
    cursor: pointer;
  }
  .btn.primary {
    border-color: transparent;
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: default;
  }
  input[type="search"],
  input[type="number"],
  select {
    box-sizing: border-box;
    height: 36px;
    padding: 0 8px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--card-background-color);
  }
  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    margin: 0;
    flex: none;
    accent-color: var(--primary-color);
  }
  :is(button, input, select, .toggle):focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 1px;
  }
  label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }
  .secondary {
    color: var(--secondary-text-color);
    font-size: 0.875rem;
    line-height: 1.35;
  }

  /* Banners */
  .banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    border-left: 4px solid var(--info-color, var(--primary-color));
    background: color-mix(in srgb, var(--info-color, var(--primary-color)) 12%, var(--card-background-color));
    line-height: 1.4;
  }
  .banner > span {
    flex: 1;
  }
  .banner.warning {
    border-color: var(--warning-color);
    background: color-mix(in srgb, var(--warning-color) 16%, var(--card-background-color));
  }
  .banner.error {
    border-color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 14%, var(--card-background-color));
  }
  .banner.ok {
    border-color: var(--success-color);
    background: color-mix(in srgb, var(--success-color) 14%, var(--card-background-color));
  }
  .banner.pump {
    font-weight: 500;
  }

  /* Search, filter and the actions on all parameters */
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 12px;
  }
  .toolbar input[type="search"] {
    flex: 1 1 16rem;
    min-width: 0;
  }
  .toolbar .baseline-text {
    flex: 1 1 14rem;
  }

  /* Groups */
  .group {
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--card-background-color);
    overflow: hidden;
  }
  .group-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-right: 12px;
  }
  .toggle {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 8px 12px 12px;
    border: 0;
    background: none;
    text-align: left;
    cursor: pointer;
  }
  .toggle ha-icon {
    flex: none;
    color: var(--secondary-text-color);
    transition: transform 0.15s;
  }
  .toggle[aria-expanded="true"] ha-icon {
    transform: rotate(90deg);
  }
  .toggle .title {
    font-weight: 500;
  }
  .toggle .count {
    display: block;
    font-weight: 400;
  }
  .group-body {
    border-top: 1px solid var(--divider-color);
  }
  .group-body > .banner,
  .group-body > .note {
    margin: 12px;
  }
  .note {
    color: var(--secondary-text-color);
  }

  /* One parameter */
  .row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 17rem) 11rem;
    gap: 8px 20px;
    padding: 12px 16px 12px 13px;
    border-left: 3px solid transparent;
  }
  .row + .row {
    border-top: 1px solid var(--divider-color);
  }
  .row.differs {
    border-left-color: var(--accent-color);
  }
  .loading .row {
    opacity: 0.55;
  }
  .what {
    display: flex;
    gap: 8px;
  }
  .name {
    font-weight: 500;
  }
  .code {
    flex: none;
    min-width: 2.8rem;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }
  .value {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }
  .current,
  .editor {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    min-height: 36px;
  }
  .number {
    flex: 1;
    min-width: 0;
    font-size: 1.05rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }
  .editor input {
    width: 5rem;
  }
  .editor select {
    flex: 1 1 100%;
    min-width: 0;
    max-width: 100%;
  }
  .tag,
  .pill {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    white-space: nowrap;
  }
  .tag {
    color: var(--secondary-text-color);
    border: 1px solid var(--divider-color);
  }
  .pill {
    color: var(--text-accent-color, #fff);
    background: var(--accent-color);
  }
  .baseline {
    font-size: 0.875rem;
  }
  .result {
    font-size: 0.875rem;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }
  .result.ok {
    color: var(--success-color);
  }
  .result.error {
    color: var(--error-color);
  }
  .choices {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 0.875rem;
  }
  .choices label.staged {
    color: var(--primary-color);
    font-weight: 500;
  }
  .choices label.staged::after {
    content: "•";
  }
  @container (max-width: 760px) {
    .inner {
      padding: 12px 8px;
    }
    .pinned {
      padding: 12px 8px;
    }
    .row {
      grid-template-columns: minmax(0, 1fr);
    }
    .choices {
      flex-direction: row;
      flex-wrap: wrap;
      gap: 8px 20px;
    }
  }

  /* Staged choices */
  .bar {
    flex: none;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 8px 12px;
    padding: 10px 16px;
    border-top: 1px solid var(--divider-color);
    background: var(--card-background-color);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.12);
  }
  .bar > span {
    flex: 1 1 14rem;
  }

  /* Confirmations */
  dialog {
    box-sizing: border-box;
    width: min(30rem, calc(100vw - 32px));
    padding: 20px;
    border: 0;
    border-radius: var(--ha-card-border-radius, 12px);
    color: var(--primary-text-color);
    background: var(--card-background-color);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  }
  dialog::backdrop {
    background: rgba(0, 0, 0, 0.5);
  }
  dialog h2 {
    margin: 0 0 12px;
    font-size: 1.25rem;
    font-weight: 400;
  }
  dialog p {
    margin: 0 0 12px;
    line-height: 1.4;
  }
  dialog dl {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 6px 16px;
    margin: 0 0 12px;
  }
  dialog dt {
    color: var(--secondary-text-color);
  }
  dialog dd {
    margin: 0;
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  dialog .buttons {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 20px;
  }
`, $ = (e) => e?.message ?? String(e);
function Ie(e, t) {
	let n = document.createElement("a");
	n.href = URL.createObjectURL(new Blob([t], { type: "application/json" })), n.download = e, n.click(), setTimeout(() => URL.revokeObjectURL(n.href), 1e3);
}
var Le = class extends G {
	static {
		this.properties = {
			hass: { attribute: !1 },
			narrow: { type: Boolean },
			route: { attribute: !1 },
			panel: { attribute: !1 },
			_data: { state: !0 },
			_error: { state: !0 },
			_query: { state: !0 },
			_differing: { state: !0 },
			_open: { state: !0 },
			_reads: { state: !0 },
			_staged: { state: !0 },
			_edit: { state: !0 },
			_writing: { state: !0 },
			_result: { state: !0 },
			_confirm: { state: !0 },
			_busy: { state: !0 },
			_notice: { state: !0 }
		};
	}
	static {
		this.styles = Fe;
	}
	constructor() {
		super(), this._started = !1, this.narrow = !1, this._data = null, this._error = null, this._query = "", this._differing = !1, this._open = /* @__PURE__ */ new Set(), this._reads = {}, this._staged = null, this._edit = null, this._writing = null, this._result = null, this._confirm = null, this._busy = null, this._notice = null;
	}
	updated(e) {
		this.hass && !this._started && (this._started = !0, this._load());
		let t = this.renderRoot.querySelector("dialog");
		this._confirm && !t?.open && t?.showModal(), !this._confirm && t?.open && t.close(), e.has("_edit") && this._edit && !e.get("_edit") && this.renderRoot.querySelector(".editor input, .editor select")?.focus();
	}
	get _entry() {
		return this._data?.entries.find((e) => e.entry_id === this._data?.entry_id);
	}
	_call(e, t = {}) {
		return this.hass.callWS({
			type: `adlar_heatpump/${e}`,
			entry_id: this._data?.entry_id,
			...t
		});
	}
	async _load(e = this._data?.entry_id) {
		try {
			this._data = await this._call("list", { entry_id: e ?? void 0 }), this._error = null;
		} catch (e) {
			this._error = $(e);
		}
	}
	_select(e) {
		this._open = /* @__PURE__ */ new Set(), this._reads = {}, this._staged = null, this._edit = null, this._result = null, this._notice = null, this._load(e);
	}
	_toggle(e) {
		let t = !this._open.has(e.id);
		this._open = Te(this._open, e.id, t), t && this._entry?.loaded && this._read(e.id), !t && e.parameters.some((e) => e.key === this._edit?.key) && (this._edit = null);
	}
	async _read(e) {
		let t = this._data?.entry_id, n = () => this._data?.entry_id === t;
		this._reads = {
			...this._reads,
			[e]: { reading: !0 }
		};
		let r;
		try {
			let { values: t } = await this._call("read_group", { group: e });
			n() && (this._data = {
				...this._data,
				groups: Se(this._data.groups, t)
			});
		} catch (e) {
			r = $(e);
		}
		n() && (this._reads = {
			...this._reads,
			[e]: { error: r }
		});
	}
	_filter(e) {
		Object.assign(this, e), this._edit = null;
	}
	_askWrite(e, t) {
		let n = X(e);
		this._confirm = {
			title: K.confirmWriteTitle,
			body: P`<p><strong>${q(e)}</strong></p>
        <dl>
          <dt>${K.oldValue}</dt>
          <dd>${Y(e, e.value)}</dd>
          <dt>${K.newValueShort}</dt>
          <dd>${Y(e, t)}</dd>
          ${n ? P`<dt>${K.rangeLabel}</dt><dd>${n}</dd>` : I}
        </dl>
        ${e.warning ? P`<p class="banner warning">${K.warnings[e.warning]}</p>` : I}`,
			confirm: K.confirmWrite,
			action: () => this._write(e, t)
		};
	}
	async _write(e, t) {
		this._edit = null, this._result = null, this._writing = e.key;
		let n = !1;
		try {
			let n = await this._call("write", {
				key: e.key,
				value: t
			});
			this._data = {
				...this._data,
				groups: Se(this._data.groups, { [e.key]: n.value })
			}, this._result = {
				key: e.key,
				ok: !0,
				text: K.written(Y(e, n.value))
			};
		} catch (t) {
			n = !0, this._result = {
				key: e.key,
				ok: !1,
				text: K.notWritten($(t))
			};
		}
		this._writing = null;
		let r = this._data.groups.find((t) => t.parameters.some((t) => t.key === e.key));
		n && r && await this._read(r.id), e.warning === "dc_pump" && await this._load();
	}
	_choose(e, t, n) {
		let r = () => {
			let r = this._staged ?? Q(this._data.groups);
			this._staged = {
				...r,
				[t]: Te(r[t], e.key, n)
			};
		};
		if (!(t === "automations" && n && we(e))) return r();
		this._confirm = {
			title: K.confirmAutomationTitle,
			body: P`<p><strong>${q(e)}</strong></p>
        <p class="banner warning">${K.warnings[e.warning]}</p>
        <p>${K.confirmAutomationBody}</p>`,
			confirm: K.confirmAutomation,
			action: r
		};
	}
	_recommend() {
		let e = this._staged ?? Q(this._data.groups);
		this._staged = {
			...e,
			sensors: new Set(this._data.recommended)
		};
	}
	async _run(e, t) {
		this._busy = e, this._notice = null, this._edit = null;
		try {
			this._notice = {
				ok: !0,
				text: await t()
			};
		} catch (e) {
			this._notice = {
				ok: !1,
				text: $(e)
			};
		}
		this._busy = null;
	}
	_apply() {
		return this._run(K.applying, async () => {
			if (await this._call("set_choices", Oe(this._staged)), this._staged = null, this._result = null, await this._load(), this._entry?.loaded) for (let e of this._open) await this._read(e);
			return K.applied;
		});
	}
	_askBaseline() {
		this._confirm = {
			title: K.setBaselineTitle,
			body: P`<p>${K.setBaselineBody}</p>`,
			confirm: K.setBaseline,
			action: () => this._run(K.settingBaseline, async () => (await this._call("set_baseline"), await this._load(), K.baselineSet))
		};
	}
	_export() {
		return this._run(K.exporting, async () => {
			let { parameters: e } = await this._call("export"), t = ke(this._entry.title, /* @__PURE__ */ new Date(), e);
			return Ie(t.name, t.content), K.exported(t.name);
		});
	}
	_confirmed() {
		let e = this._confirm.action;
		this._confirm = null, e();
	}
	render() {
		let e = this._data, t = e ? this._staged ?? Q(e.groups) : null, n = e && t ? De(Q(e.groups), t) : 0, r = n > 0 || this._busy !== null || this._writing !== null;
		return P`<div class="page" style="color-scheme: ${this.hass?.themes?.darkMode ? "dark" : "light"}">
      <div class="header">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <h1>${K.title}</h1>
        ${e && e.entries.length > 1 ? P`<select
              aria-label=${K.heatPump}
              title=${n > 0 ? K.stagedFirst : ""}
              ?disabled=${r}
              @change=${(e) => this._select(e.target.value)}
            >
              ${e.entries.map((t) => P`<option value=${t.entry_id} ?selected=${t.entry_id === e.entry_id}>
                    ${t.title}
                  </option>`)}
            </select>` : I}
      </div>
      ${this._pinned()}
      <div class="content">
        <div class="inner">
          ${e && t ? this._body(e, t) : this._error ? I : P`<div class="note">${K.loading}</div>`}
        </div>
      </div>
      ${n > 0 ? P`<div class="bar">
            <span><strong>${K.staged(n)}</strong> ${K.applyHint}</span>
            <button class="btn" ?disabled=${this._busy !== null} @click=${() => this._staged = null}>
              ${K.discard}
            </button>
            <button class="btn primary" ?disabled=${this._busy !== null} @click=${this._apply}>
              ${this._busy === K.applying ? K.applying : K.apply}
            </button>
          </div>` : I}
      <dialog aria-labelledby="confirm-title" @close=${() => this._confirm = null}>
        ${this._confirm ? P`<h2 id="confirm-title">${this._confirm.title}</h2>
              ${this._confirm.body}
              <div class="buttons">
                <button class="btn" @click=${() => this._confirm = null}>${K.cancel}</button>
                <button class="btn primary" @click=${this._confirmed}>${this._confirm.confirm}</button>
              </div>` : I}
      </dialog>
    </div>`;
	}
	_pinned() {
		return !this._data?.pump_manual && !this._error && !this._busy && !this._notice ? I : P`<div class="pinned">
      ${this._data?.pump_manual ? P`<div class="banner warning pump" role="alert">
            <ha-icon icon="mdi:alert"></ha-icon><span>${K.pumpManual}</span>
          </div>` : I}
      ${this._error ? P`<div class="banner error" role="alert">
            <span>${this._error}</span>
            <button class="btn" @click=${() => this._load()}>${K.retry}</button>
          </div>` : I}
      ${this._busy ? P`<div class="banner" role="status"><span>${this._busy}</span></div>` : I}
      ${this._notice ? P`<div class="banner ${this._notice.ok ? "ok" : "error"}" role="status">
            <span>${this._notice.text}</span>
            <button class="btn" @click=${() => this._notice = null}>${K.dismiss}</button>
          </div>` : I}
    </div>`;
	}
	_body(e, t) {
		let n = this._entry;
		if (!n) return P`<div class="note">${K.noEntries}</div>`;
		let r = xe(e.groups, this._query, this._differing), i = this._query.trim() !== "" || this._differing, a = n.loaded && this._busy === null, o = {
			idle: this._busy === null && this._writing === null && this._edit === null,
			staged: t,
			edit: this._edit,
			writing: this._writing,
			result: this._result,
			onEdit: (e) => {
				this._edit = e && {
					key: e.key,
					input: String(e.value)
				}, this._result = null;
			},
			onInput: (e) => this._edit = {
				...this._edit,
				input: e
			},
			onSave: (e, t) => this._askWrite(e, t),
			onChoice: (e, t, n) => this._choose(e, t, n)
		};
		return P`${n.loaded ? I : P`<div class="banner warning" role="alert"><span>${K.notLoaded}</span></div>`}
      <div class="toolbar">
        <input
          type="search"
          placeholder=${K.search}
          aria-label=${K.search}
          .value=${this._query}
          @input=${(e) => this._filter({ _query: e.target.value })}
        />
        <label>
          <input
            type="checkbox"
            .checked=${this._differing}
            @change=${(e) => this._filter({ _differing: e.target.checked })}
          />${K.differing}
        </label>
        <button class="btn" title=${K.recommendedHint} ?disabled=${this._busy !== null} @click=${this._recommend}>
          ${K.recommended}
        </button>
        <button class="btn" ?disabled=${!a} @click=${this._export}>${K.export}</button>
      </div>
      <div class="toolbar">
        <span class="secondary baseline-text">
          ${e.baseline_set_at ? K.baselineSetOn(new Date(e.baseline_set_at).toLocaleString(this.hass?.locale?.language, {
			dateStyle: "medium",
			timeStyle: "short"
		})) : K.baselineReference}
        </span>
        <button class="btn" ?disabled=${!a} @click=${this._askBaseline}>${K.setBaseline}</button>
      </div>
      ${r.length ? r.map((e) => this._group(e, o, i, n.loaded)) : P`<div class="note">${K.noMatches}</div>`}`;
	}
	_group(e, t, n, r) {
		let { group: i, rows: a } = e, o = this._open.has(i.id), s = this._reads[i.id] ?? {};
		return P`<section class="group">
      <div class="group-head">
        <button class="toggle" aria-expanded=${o} @click=${() => this._toggle(i)}>
          <ha-icon icon="mdi:chevron-right"></ha-icon>
          <span>
            <span class="title">${i.title}</span>
            <span class="secondary count">
              ${n ? K.shownOf(a.length, i.parameters.length) : K.parameters(i.parameters.length)}${e.unknown ? K.unknownDiff(e.unknown) : ""}
            </span>
          </span>
        </button>
        ${o && r ? P`<button class="btn" ?disabled=${s.reading || this._busy !== null} @click=${() => this._read(i.id)}>
              ${K.readAgain}
            </button>` : I}
      </div>
      ${o ? P`<div class="group-body ${s.reading ? "loading" : ""}">
            ${s.reading ? P`<div class="note" role="status">${K.reading}</div>` : I}
            ${s.error ? P`<div class="banner error" role="alert"><span>${K.readFailed(s.error)}</span></div>` : I}
            ${a.length ? a.map((e) => Pe(e, {
			...t,
			idle: t.idle && !s.reading
		})) : P`<div class="note">${K.noRows}</div>`}
          </div>` : I}
    </section>`;
	}
};
customElements.get("adlar-parameters-panel") || customElements.define("adlar-parameters-panel", Le);
//#endregion
export { Le as AdlarParametersPanel };
