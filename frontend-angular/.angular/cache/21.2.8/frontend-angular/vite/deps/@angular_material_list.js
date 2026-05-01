import {
  MatPseudoCheckboxModule
} from "./chunk-5FXN2NBL.js";
import {
  SelectionModel
} from "./chunk-UFXQEMIF.js";
import {
  MatDivider,
  MatDividerModule
} from "./chunk-LF4RH6MB.js";
import {
  MatRippleModule
} from "./chunk-JYHBJ2LR.js";
import {
  MAT_RIPPLE_GLOBAL_OPTIONS,
  RippleRenderer,
  _StructuralStylesLoader
} from "./chunk-DHOGQPG2.js";
import "./chunk-QQDH6FWE.js";
import {
  A,
  CdkObserveContent,
  ENTER,
  FocusKeyManager,
  ObserversModule,
  SPACE,
  hasModifierKey
} from "./chunk-ED6U2CG7.js";
import {
  _getFocusedElementPierceShadowDom
} from "./chunk-ZI64A6ET.js";
import {
  _animationsDisabled
} from "./chunk-OQUDMRP6.js";
import {
  coerceBooleanProperty
} from "./chunk-42QFQP6S.js";
import "./chunk-N4DOILP3.js";
import "./chunk-OIEYNCLA.js";
import "./chunk-W6W4T236.js";
import "./chunk-EKHNZ4HL.js";
import "./chunk-SAPXHBS3.js";
import "./chunk-5MX34KEC.js";
import "./chunk-GUGIMSVJ.js";
import {
  _CdkPrivateStyleLoader
} from "./chunk-N4JL6T4W.js";
import {
  Platform
} from "./chunk-QGDRJY7O.js";
import {
  coerceNumberProperty
} from "./chunk-CLNITE2V.js";
import {
  BidiModule
} from "./chunk-FX4ZE7D7.js";
import {
  NG_VALUE_ACCESSOR
} from "./chunk-M7CRW6RK.js";
import {
  NgTemplateOutlet
} from "./chunk-G45XYM2O.js";
import "./chunk-QVYI6HPX.js";
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ContentChildren,
  Directive,
  ElementRef,
  EventEmitter,
  InjectionToken,
  Injector,
  Input,
  NgModule,
  NgZone,
  Output,
  Renderer2,
  ViewChild,
  ViewEncapsulation,
  forwardRef,
  inject,
  setClassMetadata,
  signal,
  ɵɵInheritDefinitionFeature,
  ɵɵNgOnChangesFeature,
  ɵɵProvidersFeature,
  ɵɵadvance,
  ɵɵattribute,
  ɵɵclassProp,
  ɵɵconditional,
  ɵɵconditionalCreate,
  ɵɵcontentQuery,
  ɵɵdefineComponent,
  ɵɵdefineDirective,
  ɵɵdefineInjector,
  ɵɵdefineNgModule,
  ɵɵelement,
  ɵɵelementEnd,
  ɵɵelementStart,
  ɵɵgetInheritedFactory,
  ɵɵlistener,
  ɵɵloadQuery,
  ɵɵnamespaceHTML,
  ɵɵnamespaceSVG,
  ɵɵnextContext,
  ɵɵprojection,
  ɵɵprojectionDef,
  ɵɵproperty,
  ɵɵqueryRefresh,
  ɵɵreference,
  ɵɵtemplate,
  ɵɵtemplateRefExtractor,
  ɵɵviewQuery
} from "./chunk-GB2S65Z7.js";
import {
  Subject,
  Subscription,
  merge,
  takeUntil
} from "./chunk-RSS3ODKE.js";
import "./chunk-GOMI4DH3.js";

// node_modules/@angular/material/fesm2022/list.mjs
var _c0 = ["*"];
var _c1 = '.mdc-list {\n  margin: 0;\n  padding: 8px 0;\n  list-style-type: none;\n}\n.mdc-list:focus {\n  outline: none;\n}\n\n.mdc-list-item {\n  display: flex;\n  position: relative;\n  justify-content: flex-start;\n  overflow: hidden;\n  padding: 0;\n  align-items: stretch;\n  cursor: pointer;\n  padding-left: 16px;\n  padding-right: 16px;\n  background-color: var(--mat-list-list-item-container-color, transparent);\n  border-radius: var(--mat-list-list-item-container-shape, var(--mat-sys-corner-none));\n}\n.mdc-list-item.mdc-list-item--selected {\n  background-color: var(--mat-list-list-item-selected-container-color);\n}\n.mdc-list-item:focus {\n  outline: 0;\n}\n.mdc-list-item.mdc-list-item--disabled {\n  cursor: auto;\n}\n.mdc-list-item.mdc-list-item--with-one-line {\n  height: var(--mat-list-list-item-one-line-container-height, 48px);\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__start {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-two-lines {\n  height: var(--mat-list-list-item-two-line-container-height, 64px);\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-three-lines {\n  height: var(--mat-list-list-item-three-line-container-height, 88px);\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--selected::before, .mdc-list-item.mdc-list-item--selected:focus::before, .mdc-list-item:not(.mdc-list-item--selected):focus::before {\n  position: absolute;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  content: "";\n  pointer-events: none;\n}\n\na.mdc-list-item {\n  color: inherit;\n  text-decoration: none;\n}\n\n.mdc-list-item__start {\n  fill: currentColor;\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-leading-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-leading-icon-size, 24px);\n  height: var(--mat-list-list-item-leading-icon-size, 24px);\n  margin-left: 16px;\n  margin-right: 32px;\n}\n[dir=rtl] .mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-left: 32px;\n  margin-right: 16px;\n}\n.mdc-list-item--with-leading-icon:hover .mdc-list-item__start {\n  color: var(--mat-list-list-item-hover-leading-icon-color);\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  width: var(--mat-list-list-item-leading-avatar-size, 40px);\n  height: var(--mat-list-list-item-leading-avatar-size, 40px);\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start, [dir=rtl] .mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n\n.mdc-list-item__end {\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  font-family: var(--mat-list-list-item-trailing-supporting-text-font, var(--mat-sys-label-small-font));\n  line-height: var(--mat-list-list-item-trailing-supporting-text-line-height, var(--mat-sys-label-small-line-height));\n  font-size: var(--mat-list-list-item-trailing-supporting-text-size, var(--mat-sys-label-small-size));\n  font-weight: var(--mat-list-list-item-trailing-supporting-text-weight, var(--mat-sys-label-small-weight));\n  letter-spacing: var(--mat-list-list-item-trailing-supporting-text-tracking, var(--mat-sys-label-small-tracking));\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-trailing-icon-size, 24px);\n  height: var(--mat-list-list-item-trailing-icon-size, 24px);\n}\n.mdc-list-item--with-trailing-icon:hover .mdc-list-item__end {\n  color: var(--mat-list-list-item-hover-trailing-icon-color);\n}\n.mdc-list-item.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-supporting-text-color, var(--mat-sys-on-surface-variant));\n}\n.mdc-list-item--selected.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-selected-trailing-icon-color, var(--mat-sys-primary));\n}\n\n.mdc-list-item__content {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  align-self: center;\n  flex: 1;\n  pointer-events: none;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__content, .mdc-list-item--with-three-lines .mdc-list-item__content {\n  align-self: stretch;\n}\n\n.mdc-list-item__primary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  color: var(--mat-list-list-item-label-text-color, var(--mat-sys-on-surface));\n  font-family: var(--mat-list-list-item-label-text-font, var(--mat-sys-body-large-font));\n  line-height: var(--mat-list-list-item-label-text-line-height, var(--mat-sys-body-large-line-height));\n  font-size: var(--mat-list-list-item-label-text-size, var(--mat-sys-body-large-size));\n  font-weight: var(--mat-list-list-item-label-text-weight, var(--mat-sys-body-large-weight));\n  letter-spacing: var(--mat-list-list-item-label-text-tracking, var(--mat-sys-body-large-tracking));\n}\n.mdc-list-item:hover .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-hover-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item:focus .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-focus-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text, .mdc-list-item--with-three-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n\n.mdc-list-item__secondary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  display: block;\n  margin-top: 0;\n  color: var(--mat-list-list-item-supporting-text-color, var(--mat-sys-on-surface-variant));\n  font-family: var(--mat-list-list-item-supporting-text-font, var(--mat-sys-body-medium-font));\n  line-height: var(--mat-list-list-item-supporting-text-line-height, var(--mat-sys-body-medium-line-height));\n  font-size: var(--mat-list-list-item-supporting-text-size, var(--mat-sys-body-medium-size));\n  font-weight: var(--mat-list-list-item-supporting-text-weight, var(--mat-sys-body-medium-weight));\n  letter-spacing: var(--mat-list-list-item-supporting-text-tracking, var(--mat-sys-body-medium-tracking));\n}\n.mdc-list-item__secondary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-three-lines .mdc-list-item__secondary-text {\n  white-space: normal;\n  line-height: 20px;\n}\n.mdc-list-item--with-overline .mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: auto;\n}\n\n.mdc-list-item--with-leading-radio.mdc-list-item,\n.mdc-list-item--with-leading-checkbox.mdc-list-item,\n.mdc-list-item--with-leading-icon.mdc-list-item,\n.mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-checkbox.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-icon.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-trailing-icon.mdc-list-item, [dir=rtl] .mdc-list-item--with-trailing-icon.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n}\n\n.mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  -webkit-user-select: none;\n  user-select: none;\n  margin-left: 28px;\n  margin-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 28px;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end {\n  display: block;\n  line-height: normal;\n  align-self: flex-start;\n  margin-top: 0;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end::before, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-leading-radio .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio .mdc-list-item__start,\n[dir=rtl] .mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-item--with-trailing-radio.mdc-list-item,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-left: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, [dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-radio .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio .mdc-list-item__end,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-three-lines .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-group__subheader {\n  margin: 0.75rem 16px;\n}\n\n.mdc-list-item--disabled .mdc-list-item__start,\n.mdc-list-item--disabled .mdc-list-item__content,\n.mdc-list-item--disabled .mdc-list-item__end {\n  opacity: 1;\n}\n.mdc-list-item--disabled .mdc-list-item__primary-text,\n.mdc-list-item--disabled .mdc-list-item__secondary-text {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n.mdc-list-item--disabled.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-disabled-leading-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-leading-icon-opacity, 0.38);\n}\n.mdc-list-item--disabled.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-disabled-trailing-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-trailing-icon-opacity, 0.38);\n}\n\n.mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing, [dir=rtl] .mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing {\n  padding-left: 0;\n  padding-right: 0;\n}\n\n.mdc-list-item.mdc-list-item--disabled .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-disabled-label-text-color, var(--mat-sys-on-surface));\n}\n\n.mdc-list-item:hover::before {\n  background-color: var(--mat-list-list-item-hover-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-hover-state-layer-opacity, var(--mat-sys-hover-state-layer-opacity));\n}\n\n.mdc-list-item.mdc-list-item--disabled::before {\n  background-color: var(--mat-list-list-item-disabled-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item:focus::before {\n  background-color: var(--mat-list-list-item-focus-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-focus-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item--disabled .mdc-radio,\n.mdc-list-item--disabled .mdc-checkbox {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n\n.mdc-list-item--with-leading-avatar .mat-mdc-list-item-avatar {\n  border-radius: var(--mat-list-list-item-leading-avatar-shape, var(--mat-sys-corner-full));\n  background-color: var(--mat-list-list-item-leading-avatar-color, var(--mat-sys-primary-container));\n}\n\n.mat-mdc-list-item-icon {\n  font-size: var(--mat-list-list-item-leading-icon-size, 24px);\n}\n\n@media (forced-colors: active) {\n  a.mdc-list-item--activated::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  a.mdc-list-item--activated [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n\n.mat-mdc-list-base {\n  display: block;\n}\n.mat-mdc-list-base .mdc-list-item__start,\n.mat-mdc-list-base .mdc-list-item__end,\n.mat-mdc-list-base .mdc-list-item__content {\n  pointer-events: auto;\n}\n\n.mat-mdc-list-item,\n.mat-mdc-list-option {\n  width: 100%;\n  box-sizing: border-box;\n  -webkit-tap-highlight-color: transparent;\n}\n.mat-mdc-list-item:not(.mat-mdc-list-item-interactive),\n.mat-mdc-list-option:not(.mat-mdc-list-item-interactive) {\n  cursor: default;\n}\n.mat-mdc-list-item .mat-divider-inset,\n.mat-mdc-list-option .mat-divider-inset {\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n.mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n.mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-left: 72px;\n}\n[dir=rtl] .mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n[dir=rtl] .mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-right: 72px;\n}\n\n.mat-mdc-list-item-interactive::before {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  content: "";\n  opacity: 0;\n  pointer-events: none;\n  border-radius: inherit;\n}\n\n.mat-mdc-list-item > .mat-focus-indicator {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  pointer-events: none;\n}\n.mat-mdc-list-item:focus-visible > .mat-focus-indicator::before {\n  content: "";\n}\n\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-line.mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: normal;\n}\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-unscoped-content.mdc-list-item__secondary-text {\n  display: -webkit-box;\n  -webkit-box-orient: vertical;\n  -webkit-line-clamp: 2;\n}\n\nmat-action-list button {\n  background: none;\n  color: inherit;\n  border: none;\n  font: inherit;\n  outline: inherit;\n  -webkit-tap-highlight-color: transparent;\n  text-align: start;\n}\nmat-action-list button::-moz-focus-inner {\n  border: 0;\n}\n\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-inline-start: var(--mat-list-list-item-leading-icon-start-space, 16px);\n  margin-inline-end: var(--mat-list-list-item-leading-icon-end-space, 16px);\n}\n\n.mat-mdc-nav-list .mat-mdc-list-item {\n  border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n  --mat-focus-indicator-border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n}\n.mat-mdc-nav-list .mat-mdc-list-item.mdc-list-item--activated {\n  background-color: var(--mat-list-active-indicator-color, var(--mat-sys-secondary-container));\n}\n';
var _c2 = ["unscopedContent"];
var _c3 = ["text"];
var _c4 = [[["", "matListItemAvatar", ""], ["", "matListItemIcon", ""]], [["", "matListItemTitle", ""]], [["", "matListItemLine", ""]], "*", [["", "matListItemMeta", ""]], [["mat-divider"]]];
var _c5 = ["[matListItemAvatar],[matListItemIcon]", "[matListItemTitle]", "[matListItemLine]", "*", "[matListItemMeta]", "mat-divider"];
var _c6 = [[["", "matListItemTitle", ""]], [["", "matListItemLine", ""]], "*", [["mat-divider"]], [["", "matListItemAvatar", ""], ["", "matListItemIcon", ""]]];
var _c7 = ["[matListItemTitle]", "[matListItemLine]", "*", "mat-divider", "[matListItemAvatar],[matListItemIcon]"];
function MatListOption_ng_template_0_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵprojection(0, 4);
  }
}
function MatListOption_ng_template_2_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "div", 11);
    ɵɵelement(1, "input", 12);
    ɵɵelementStart(2, "div", 13);
    ɵɵnamespaceSVG();
    ɵɵelementStart(3, "svg", 14);
    ɵɵelement(4, "path", 15);
    ɵɵelementEnd();
    ɵɵnamespaceHTML();
    ɵɵelement(5, "div", 16);
    ɵɵelementEnd()();
  }
  if (rf & 2) {
    const ctx_r0 = ɵɵnextContext();
    ɵɵclassProp("mdc-checkbox--disabled", ctx_r0.disabled);
    ɵɵadvance();
    ɵɵproperty("checked", ctx_r0.selected)("disabled", ctx_r0.disabled);
  }
}
function MatListOption_ng_template_4_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "div", 17);
    ɵɵelement(1, "input", 18);
    ɵɵelementStart(2, "div", 19);
    ɵɵelement(3, "div", 20)(4, "div", 21);
    ɵɵelementEnd()();
  }
  if (rf & 2) {
    const ctx_r0 = ɵɵnextContext();
    ɵɵclassProp("mdc-radio--disabled", ctx_r0.disabled);
    ɵɵadvance();
    ɵɵproperty("checked", ctx_r0.selected)("disabled", ctx_r0.disabled);
  }
}
function MatListOption_Conditional_6_ng_template_1_Template(rf, ctx) {
}
function MatListOption_Conditional_6_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "span", 4);
    ɵɵtemplate(1, MatListOption_Conditional_6_ng_template_1_Template, 0, 0, "ng-template", 6);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    ɵɵnextContext();
    const checkbox_r2 = ɵɵreference(3);
    ɵɵadvance();
    ɵɵproperty("ngTemplateOutlet", checkbox_r2);
  }
}
function MatListOption_Conditional_7_ng_template_1_Template(rf, ctx) {
}
function MatListOption_Conditional_7_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "span", 5);
    ɵɵtemplate(1, MatListOption_Conditional_7_ng_template_1_Template, 0, 0, "ng-template", 6);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    ɵɵnextContext();
    const radio_r3 = ɵɵreference(5);
    ɵɵadvance();
    ɵɵproperty("ngTemplateOutlet", radio_r3);
  }
}
function MatListOption_Conditional_8_ng_template_0_Template(rf, ctx) {
}
function MatListOption_Conditional_8_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵtemplate(0, MatListOption_Conditional_8_ng_template_0_Template, 0, 0, "ng-template", 6);
  }
  if (rf & 2) {
    ɵɵnextContext();
    const icons_r4 = ɵɵreference(1);
    ɵɵproperty("ngTemplateOutlet", icons_r4);
  }
}
function MatListOption_Conditional_15_ng_template_1_Template(rf, ctx) {
}
function MatListOption_Conditional_15_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "span", 9);
    ɵɵtemplate(1, MatListOption_Conditional_15_ng_template_1_Template, 0, 0, "ng-template", 6);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    ɵɵnextContext();
    const checkbox_r2 = ɵɵreference(3);
    ɵɵadvance();
    ɵɵproperty("ngTemplateOutlet", checkbox_r2);
  }
}
function MatListOption_Conditional_16_ng_template_1_Template(rf, ctx) {
}
function MatListOption_Conditional_16_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "span", 9);
    ɵɵtemplate(1, MatListOption_Conditional_16_ng_template_1_Template, 0, 0, "ng-template", 6);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    ɵɵnextContext();
    const radio_r3 = ɵɵreference(5);
    ɵɵadvance();
    ɵɵproperty("ngTemplateOutlet", radio_r3);
  }
}
function MatListOption_Conditional_17_ng_template_0_Template(rf, ctx) {
}
function MatListOption_Conditional_17_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵtemplate(0, MatListOption_Conditional_17_ng_template_0_Template, 0, 0, "ng-template", 6);
  }
  if (rf & 2) {
    ɵɵnextContext();
    const icons_r4 = ɵɵreference(1);
    ɵɵproperty("ngTemplateOutlet", icons_r4);
  }
}
var LIST_OPTION = new InjectionToken("ListOption");
var MatListItemTitle = class _MatListItemTitle {
  _elementRef = inject(ElementRef);
  constructor() {
  }
  static ɵfac = function MatListItemTitle_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListItemTitle)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: _MatListItemTitle,
    selectors: [["", "matListItemTitle", ""]],
    hostAttrs: [1, "mat-mdc-list-item-title", "mdc-list-item__primary-text"]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItemTitle, [{
    type: Directive,
    args: [{
      selector: "[matListItemTitle]",
      host: {
        "class": "mat-mdc-list-item-title mdc-list-item__primary-text"
      }
    }]
  }], () => [], null);
})();
var MatListItemLine = class _MatListItemLine {
  _elementRef = inject(ElementRef);
  constructor() {
  }
  static ɵfac = function MatListItemLine_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListItemLine)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: _MatListItemLine,
    selectors: [["", "matListItemLine", ""]],
    hostAttrs: [1, "mat-mdc-list-item-line", "mdc-list-item__secondary-text"]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItemLine, [{
    type: Directive,
    args: [{
      selector: "[matListItemLine]",
      host: {
        "class": "mat-mdc-list-item-line mdc-list-item__secondary-text"
      }
    }]
  }], () => [], null);
})();
var MatListItemMeta = class _MatListItemMeta {
  static ɵfac = function MatListItemMeta_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListItemMeta)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: _MatListItemMeta,
    selectors: [["", "matListItemMeta", ""]],
    hostAttrs: [1, "mat-mdc-list-item-meta", "mdc-list-item__end"]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItemMeta, [{
    type: Directive,
    args: [{
      selector: "[matListItemMeta]",
      host: {
        "class": "mat-mdc-list-item-meta mdc-list-item__end"
      }
    }]
  }], null, null);
})();
var _MatListItemGraphicBase = class __MatListItemGraphicBase {
  _listOption = inject(LIST_OPTION, {
    optional: true
  });
  constructor() {
  }
  _isAlignedAtStart() {
    return !this._listOption || this._listOption?._getTogglePosition() === "after";
  }
  static ɵfac = function _MatListItemGraphicBase_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || __MatListItemGraphicBase)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: __MatListItemGraphicBase,
    hostVars: 4,
    hostBindings: function _MatListItemGraphicBase_HostBindings(rf, ctx) {
      if (rf & 2) {
        ɵɵclassProp("mdc-list-item__start", ctx._isAlignedAtStart())("mdc-list-item__end", !ctx._isAlignedAtStart());
      }
    }
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(_MatListItemGraphicBase, [{
    type: Directive,
    args: [{
      host: {
        "[class.mdc-list-item__start]": "_isAlignedAtStart()",
        "[class.mdc-list-item__end]": "!_isAlignedAtStart()"
      }
    }]
  }], () => [], null);
})();
var MatListItemAvatar = class _MatListItemAvatar extends _MatListItemGraphicBase {
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatListItemAvatar_BaseFactory;
    return function MatListItemAvatar_Factory(__ngFactoryType__) {
      return (ɵMatListItemAvatar_BaseFactory || (ɵMatListItemAvatar_BaseFactory = ɵɵgetInheritedFactory(_MatListItemAvatar)))(__ngFactoryType__ || _MatListItemAvatar);
    };
  })();
  static ɵdir = ɵɵdefineDirective({
    type: _MatListItemAvatar,
    selectors: [["", "matListItemAvatar", ""]],
    hostAttrs: [1, "mat-mdc-list-item-avatar"],
    features: [ɵɵInheritDefinitionFeature]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItemAvatar, [{
    type: Directive,
    args: [{
      selector: "[matListItemAvatar]",
      host: {
        "class": "mat-mdc-list-item-avatar"
      }
    }]
  }], null, null);
})();
var MatListItemIcon = class _MatListItemIcon extends _MatListItemGraphicBase {
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatListItemIcon_BaseFactory;
    return function MatListItemIcon_Factory(__ngFactoryType__) {
      return (ɵMatListItemIcon_BaseFactory || (ɵMatListItemIcon_BaseFactory = ɵɵgetInheritedFactory(_MatListItemIcon)))(__ngFactoryType__ || _MatListItemIcon);
    };
  })();
  static ɵdir = ɵɵdefineDirective({
    type: _MatListItemIcon,
    selectors: [["", "matListItemIcon", ""]],
    hostAttrs: [1, "mat-mdc-list-item-icon"],
    features: [ɵɵInheritDefinitionFeature]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItemIcon, [{
    type: Directive,
    args: [{
      selector: "[matListItemIcon]",
      host: {
        "class": "mat-mdc-list-item-icon"
      }
    }]
  }], null, null);
})();
var MAT_LIST_CONFIG = new InjectionToken("MAT_LIST_CONFIG");
var MatListBase = class _MatListBase {
  _isNonInteractive = true;
  get disableRipple() {
    return this._disableRipple;
  }
  set disableRipple(value) {
    this._disableRipple = coerceBooleanProperty(value);
  }
  _disableRipple = false;
  get disabled() {
    return this._disabled();
  }
  set disabled(value) {
    this._disabled.set(coerceBooleanProperty(value));
  }
  _disabled = signal(false, ...ngDevMode ? [{
    debugName: "_disabled"
  }] : []);
  _defaultOptions = inject(MAT_LIST_CONFIG, {
    optional: true
  });
  static ɵfac = function MatListBase_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListBase)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: _MatListBase,
    hostVars: 1,
    hostBindings: function MatListBase_HostBindings(rf, ctx) {
      if (rf & 2) {
        ɵɵattribute("aria-disabled", ctx.disabled);
      }
    },
    inputs: {
      disableRipple: "disableRipple",
      disabled: "disabled"
    }
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListBase, [{
    type: Directive,
    args: [{
      host: {
        "[attr.aria-disabled]": "disabled"
      }
    }]
  }], null, {
    disableRipple: [{
      type: Input
    }],
    disabled: [{
      type: Input
    }]
  });
})();
var MatListItemBase = class _MatListItemBase {
  _elementRef = inject(ElementRef);
  _ngZone = inject(NgZone);
  _listBase = inject(MatListBase, {
    optional: true
  });
  _platform = inject(Platform);
  _hostElement;
  _isButtonElement;
  _noopAnimations = _animationsDisabled();
  _avatars;
  _icons;
  set lines(lines) {
    this._explicitLines = coerceNumberProperty(lines, null);
    this._updateItemLines(false);
  }
  _explicitLines = null;
  get disableRipple() {
    return this.disabled || this._disableRipple || this._noopAnimations || !!this._listBase?.disableRipple;
  }
  set disableRipple(value) {
    this._disableRipple = coerceBooleanProperty(value);
  }
  _disableRipple = false;
  get disabled() {
    return this._disabled() || !!this._listBase?.disabled;
  }
  set disabled(value) {
    this._disabled.set(coerceBooleanProperty(value));
  }
  _disabled = signal(false, ...ngDevMode ? [{
    debugName: "_disabled"
  }] : []);
  _subscriptions = new Subscription();
  _rippleRenderer = null;
  _hasUnscopedTextContent = false;
  rippleConfig;
  get rippleDisabled() {
    return this.disableRipple || !!this.rippleConfig.disabled;
  }
  constructor() {
    inject(_CdkPrivateStyleLoader).load(_StructuralStylesLoader);
    const globalRippleOptions = inject(MAT_RIPPLE_GLOBAL_OPTIONS, {
      optional: true
    });
    this.rippleConfig = globalRippleOptions || {};
    this._hostElement = this._elementRef.nativeElement;
    this._isButtonElement = this._hostElement.nodeName.toLowerCase() === "button";
    if (this._listBase && !this._listBase._isNonInteractive) {
      this._initInteractiveListItem();
    }
    if (this._isButtonElement && !this._hostElement.hasAttribute("type")) {
      this._hostElement.setAttribute("type", "button");
    }
  }
  ngAfterViewInit() {
    this._monitorProjectedLinesAndTitle();
    this._updateItemLines(true);
  }
  ngOnDestroy() {
    this._subscriptions.unsubscribe();
    if (this._rippleRenderer !== null) {
      this._rippleRenderer._removeTriggerEvents();
    }
  }
  _hasIconOrAvatar() {
    return !!(this._avatars.length || this._icons.length);
  }
  _initInteractiveListItem() {
    this._hostElement.classList.add("mat-mdc-list-item-interactive");
    this._rippleRenderer = new RippleRenderer(this, this._ngZone, this._hostElement, this._platform, inject(Injector));
    this._rippleRenderer.setupTriggerEvents(this._hostElement);
  }
  _monitorProjectedLinesAndTitle() {
    this._ngZone.runOutsideAngular(() => {
      this._subscriptions.add(merge(this._lines.changes, this._titles.changes).subscribe(() => this._updateItemLines(false)));
    });
  }
  _updateItemLines(recheckUnscopedContent) {
    if (!this._lines || !this._titles || !this._unscopedContent) {
      return;
    }
    if (recheckUnscopedContent) {
      this._checkDomForUnscopedTextContent();
    }
    if (typeof ngDevMode === "undefined" || ngDevMode) {
      sanityCheckListItemContent(this);
    }
    const numberOfLines = this._explicitLines ?? this._inferLinesFromContent();
    const unscopedContentEl = this._unscopedContent.nativeElement;
    this._hostElement.classList.toggle("mat-mdc-list-item-single-line", numberOfLines <= 1);
    this._hostElement.classList.toggle("mdc-list-item--with-one-line", numberOfLines <= 1);
    this._hostElement.classList.toggle("mdc-list-item--with-two-lines", numberOfLines === 2);
    this._hostElement.classList.toggle("mdc-list-item--with-three-lines", numberOfLines === 3);
    if (this._hasUnscopedTextContent) {
      const treatAsTitle = this._titles.length === 0 && numberOfLines === 1;
      unscopedContentEl.classList.toggle("mdc-list-item__primary-text", treatAsTitle);
      unscopedContentEl.classList.toggle("mdc-list-item__secondary-text", !treatAsTitle);
    } else {
      unscopedContentEl.classList.remove("mdc-list-item__primary-text");
      unscopedContentEl.classList.remove("mdc-list-item__secondary-text");
    }
  }
  _inferLinesFromContent() {
    let numOfLines = this._titles.length + this._lines.length;
    if (this._hasUnscopedTextContent) {
      numOfLines += 1;
    }
    return numOfLines;
  }
  _checkDomForUnscopedTextContent() {
    this._hasUnscopedTextContent = Array.from(this._unscopedContent.nativeElement.childNodes).filter((node) => node.nodeType !== node.COMMENT_NODE).some((node) => !!(node.textContent && node.textContent.trim()));
  }
  static ɵfac = function MatListItemBase_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListItemBase)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: _MatListItemBase,
    contentQueries: function MatListItemBase_ContentQueries(rf, ctx, dirIndex) {
      if (rf & 1) {
        ɵɵcontentQuery(dirIndex, MatListItemAvatar, 4)(dirIndex, MatListItemIcon, 4);
      }
      if (rf & 2) {
        let _t;
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._avatars = _t);
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._icons = _t);
      }
    },
    hostVars: 4,
    hostBindings: function MatListItemBase_HostBindings(rf, ctx) {
      if (rf & 2) {
        ɵɵattribute("aria-disabled", ctx.disabled)("disabled", ctx._isButtonElement && ctx.disabled || null);
        ɵɵclassProp("mdc-list-item--disabled", ctx.disabled);
      }
    },
    inputs: {
      lines: "lines",
      disableRipple: "disableRipple",
      disabled: "disabled"
    }
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItemBase, [{
    type: Directive,
    args: [{
      host: {
        "[class.mdc-list-item--disabled]": "disabled",
        "[attr.aria-disabled]": "disabled",
        "[attr.disabled]": "(_isButtonElement && disabled) || null"
      }
    }]
  }], () => [], {
    _avatars: [{
      type: ContentChildren,
      args: [MatListItemAvatar, {
        descendants: false
      }]
    }],
    _icons: [{
      type: ContentChildren,
      args: [MatListItemIcon, {
        descendants: false
      }]
    }],
    lines: [{
      type: Input
    }],
    disableRipple: [{
      type: Input
    }],
    disabled: [{
      type: Input
    }]
  });
})();
function sanityCheckListItemContent(item) {
  const numTitles = item._titles.length;
  const numLines = item._lines.length;
  if (numTitles > 1) {
    console.warn("A list item cannot have multiple titles.");
  }
  if (numTitles === 0 && numLines > 0) {
    console.warn("A list item line can only be used if there is a list item title.");
  }
  if (numTitles === 0 && item._hasUnscopedTextContent && item._explicitLines !== null && item._explicitLines > 1) {
    console.warn("A list item cannot have wrapping content without a title.");
  }
  if (numLines > 2 || numLines === 2 && item._hasUnscopedTextContent) {
    console.warn("A list item can have at maximum three lines.");
  }
}
var MatActionList = class _MatActionList extends MatListBase {
  _isNonInteractive = false;
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatActionList_BaseFactory;
    return function MatActionList_Factory(__ngFactoryType__) {
      return (ɵMatActionList_BaseFactory || (ɵMatActionList_BaseFactory = ɵɵgetInheritedFactory(_MatActionList)))(__ngFactoryType__ || _MatActionList);
    };
  })();
  static ɵcmp = ɵɵdefineComponent({
    type: _MatActionList,
    selectors: [["mat-action-list"]],
    hostAttrs: ["role", "group", 1, "mat-mdc-action-list", "mat-mdc-list-base", "mdc-list"],
    exportAs: ["matActionList"],
    features: [ɵɵProvidersFeature([{
      provide: MatListBase,
      useExisting: _MatActionList
    }]), ɵɵInheritDefinitionFeature],
    ngContentSelectors: _c0,
    decls: 1,
    vars: 0,
    template: function MatActionList_Template(rf, ctx) {
      if (rf & 1) {
        ɵɵprojectionDef();
        ɵɵprojection(0);
      }
    },
    styles: ['.mdc-list {\n  margin: 0;\n  padding: 8px 0;\n  list-style-type: none;\n}\n.mdc-list:focus {\n  outline: none;\n}\n\n.mdc-list-item {\n  display: flex;\n  position: relative;\n  justify-content: flex-start;\n  overflow: hidden;\n  padding: 0;\n  align-items: stretch;\n  cursor: pointer;\n  padding-left: 16px;\n  padding-right: 16px;\n  background-color: var(--mat-list-list-item-container-color, transparent);\n  border-radius: var(--mat-list-list-item-container-shape, var(--mat-sys-corner-none));\n}\n.mdc-list-item.mdc-list-item--selected {\n  background-color: var(--mat-list-list-item-selected-container-color);\n}\n.mdc-list-item:focus {\n  outline: 0;\n}\n.mdc-list-item.mdc-list-item--disabled {\n  cursor: auto;\n}\n.mdc-list-item.mdc-list-item--with-one-line {\n  height: var(--mat-list-list-item-one-line-container-height, 48px);\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__start {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-two-lines {\n  height: var(--mat-list-list-item-two-line-container-height, 64px);\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-three-lines {\n  height: var(--mat-list-list-item-three-line-container-height, 88px);\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--selected::before, .mdc-list-item.mdc-list-item--selected:focus::before, .mdc-list-item:not(.mdc-list-item--selected):focus::before {\n  position: absolute;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  content: "";\n  pointer-events: none;\n}\n\na.mdc-list-item {\n  color: inherit;\n  text-decoration: none;\n}\n\n.mdc-list-item__start {\n  fill: currentColor;\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-leading-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-leading-icon-size, 24px);\n  height: var(--mat-list-list-item-leading-icon-size, 24px);\n  margin-left: 16px;\n  margin-right: 32px;\n}\n[dir=rtl] .mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-left: 32px;\n  margin-right: 16px;\n}\n.mdc-list-item--with-leading-icon:hover .mdc-list-item__start {\n  color: var(--mat-list-list-item-hover-leading-icon-color);\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  width: var(--mat-list-list-item-leading-avatar-size, 40px);\n  height: var(--mat-list-list-item-leading-avatar-size, 40px);\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start, [dir=rtl] .mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n\n.mdc-list-item__end {\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  font-family: var(--mat-list-list-item-trailing-supporting-text-font, var(--mat-sys-label-small-font));\n  line-height: var(--mat-list-list-item-trailing-supporting-text-line-height, var(--mat-sys-label-small-line-height));\n  font-size: var(--mat-list-list-item-trailing-supporting-text-size, var(--mat-sys-label-small-size));\n  font-weight: var(--mat-list-list-item-trailing-supporting-text-weight, var(--mat-sys-label-small-weight));\n  letter-spacing: var(--mat-list-list-item-trailing-supporting-text-tracking, var(--mat-sys-label-small-tracking));\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-trailing-icon-size, 24px);\n  height: var(--mat-list-list-item-trailing-icon-size, 24px);\n}\n.mdc-list-item--with-trailing-icon:hover .mdc-list-item__end {\n  color: var(--mat-list-list-item-hover-trailing-icon-color);\n}\n.mdc-list-item.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-supporting-text-color, var(--mat-sys-on-surface-variant));\n}\n.mdc-list-item--selected.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-selected-trailing-icon-color, var(--mat-sys-primary));\n}\n\n.mdc-list-item__content {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  align-self: center;\n  flex: 1;\n  pointer-events: none;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__content, .mdc-list-item--with-three-lines .mdc-list-item__content {\n  align-self: stretch;\n}\n\n.mdc-list-item__primary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  color: var(--mat-list-list-item-label-text-color, var(--mat-sys-on-surface));\n  font-family: var(--mat-list-list-item-label-text-font, var(--mat-sys-body-large-font));\n  line-height: var(--mat-list-list-item-label-text-line-height, var(--mat-sys-body-large-line-height));\n  font-size: var(--mat-list-list-item-label-text-size, var(--mat-sys-body-large-size));\n  font-weight: var(--mat-list-list-item-label-text-weight, var(--mat-sys-body-large-weight));\n  letter-spacing: var(--mat-list-list-item-label-text-tracking, var(--mat-sys-body-large-tracking));\n}\n.mdc-list-item:hover .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-hover-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item:focus .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-focus-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text, .mdc-list-item--with-three-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n\n.mdc-list-item__secondary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  display: block;\n  margin-top: 0;\n  color: var(--mat-list-list-item-supporting-text-color, var(--mat-sys-on-surface-variant));\n  font-family: var(--mat-list-list-item-supporting-text-font, var(--mat-sys-body-medium-font));\n  line-height: var(--mat-list-list-item-supporting-text-line-height, var(--mat-sys-body-medium-line-height));\n  font-size: var(--mat-list-list-item-supporting-text-size, var(--mat-sys-body-medium-size));\n  font-weight: var(--mat-list-list-item-supporting-text-weight, var(--mat-sys-body-medium-weight));\n  letter-spacing: var(--mat-list-list-item-supporting-text-tracking, var(--mat-sys-body-medium-tracking));\n}\n.mdc-list-item__secondary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-three-lines .mdc-list-item__secondary-text {\n  white-space: normal;\n  line-height: 20px;\n}\n.mdc-list-item--with-overline .mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: auto;\n}\n\n.mdc-list-item--with-leading-radio.mdc-list-item,\n.mdc-list-item--with-leading-checkbox.mdc-list-item,\n.mdc-list-item--with-leading-icon.mdc-list-item,\n.mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-checkbox.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-icon.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-trailing-icon.mdc-list-item, [dir=rtl] .mdc-list-item--with-trailing-icon.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n}\n\n.mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  -webkit-user-select: none;\n  user-select: none;\n  margin-left: 28px;\n  margin-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 28px;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end {\n  display: block;\n  line-height: normal;\n  align-self: flex-start;\n  margin-top: 0;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end::before, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-leading-radio .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio .mdc-list-item__start,\n[dir=rtl] .mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-item--with-trailing-radio.mdc-list-item,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-left: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, [dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-radio .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio .mdc-list-item__end,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-three-lines .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-group__subheader {\n  margin: 0.75rem 16px;\n}\n\n.mdc-list-item--disabled .mdc-list-item__start,\n.mdc-list-item--disabled .mdc-list-item__content,\n.mdc-list-item--disabled .mdc-list-item__end {\n  opacity: 1;\n}\n.mdc-list-item--disabled .mdc-list-item__primary-text,\n.mdc-list-item--disabled .mdc-list-item__secondary-text {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n.mdc-list-item--disabled.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-disabled-leading-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-leading-icon-opacity, 0.38);\n}\n.mdc-list-item--disabled.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-disabled-trailing-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-trailing-icon-opacity, 0.38);\n}\n\n.mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing, [dir=rtl] .mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing {\n  padding-left: 0;\n  padding-right: 0;\n}\n\n.mdc-list-item.mdc-list-item--disabled .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-disabled-label-text-color, var(--mat-sys-on-surface));\n}\n\n.mdc-list-item:hover::before {\n  background-color: var(--mat-list-list-item-hover-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-hover-state-layer-opacity, var(--mat-sys-hover-state-layer-opacity));\n}\n\n.mdc-list-item.mdc-list-item--disabled::before {\n  background-color: var(--mat-list-list-item-disabled-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item:focus::before {\n  background-color: var(--mat-list-list-item-focus-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-focus-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item--disabled .mdc-radio,\n.mdc-list-item--disabled .mdc-checkbox {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n\n.mdc-list-item--with-leading-avatar .mat-mdc-list-item-avatar {\n  border-radius: var(--mat-list-list-item-leading-avatar-shape, var(--mat-sys-corner-full));\n  background-color: var(--mat-list-list-item-leading-avatar-color, var(--mat-sys-primary-container));\n}\n\n.mat-mdc-list-item-icon {\n  font-size: var(--mat-list-list-item-leading-icon-size, 24px);\n}\n\n@media (forced-colors: active) {\n  a.mdc-list-item--activated::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  a.mdc-list-item--activated [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n\n.mat-mdc-list-base {\n  display: block;\n}\n.mat-mdc-list-base .mdc-list-item__start,\n.mat-mdc-list-base .mdc-list-item__end,\n.mat-mdc-list-base .mdc-list-item__content {\n  pointer-events: auto;\n}\n\n.mat-mdc-list-item,\n.mat-mdc-list-option {\n  width: 100%;\n  box-sizing: border-box;\n  -webkit-tap-highlight-color: transparent;\n}\n.mat-mdc-list-item:not(.mat-mdc-list-item-interactive),\n.mat-mdc-list-option:not(.mat-mdc-list-item-interactive) {\n  cursor: default;\n}\n.mat-mdc-list-item .mat-divider-inset,\n.mat-mdc-list-option .mat-divider-inset {\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n.mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n.mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-left: 72px;\n}\n[dir=rtl] .mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n[dir=rtl] .mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-right: 72px;\n}\n\n.mat-mdc-list-item-interactive::before {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  content: "";\n  opacity: 0;\n  pointer-events: none;\n  border-radius: inherit;\n}\n\n.mat-mdc-list-item > .mat-focus-indicator {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  pointer-events: none;\n}\n.mat-mdc-list-item:focus-visible > .mat-focus-indicator::before {\n  content: "";\n}\n\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-line.mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: normal;\n}\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-unscoped-content.mdc-list-item__secondary-text {\n  display: -webkit-box;\n  -webkit-box-orient: vertical;\n  -webkit-line-clamp: 2;\n}\n\nmat-action-list button {\n  background: none;\n  color: inherit;\n  border: none;\n  font: inherit;\n  outline: inherit;\n  -webkit-tap-highlight-color: transparent;\n  text-align: start;\n}\nmat-action-list button::-moz-focus-inner {\n  border: 0;\n}\n\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-inline-start: var(--mat-list-list-item-leading-icon-start-space, 16px);\n  margin-inline-end: var(--mat-list-list-item-leading-icon-end-space, 16px);\n}\n\n.mat-mdc-nav-list .mat-mdc-list-item {\n  border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n  --mat-focus-indicator-border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n}\n.mat-mdc-nav-list .mat-mdc-list-item.mdc-list-item--activated {\n  background-color: var(--mat-list-active-indicator-color, var(--mat-sys-secondary-container));\n}\n'],
    encapsulation: 2,
    changeDetection: 0
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatActionList, [{
    type: Component,
    args: [{
      selector: "mat-action-list",
      exportAs: "matActionList",
      template: "<ng-content></ng-content>",
      host: {
        "class": "mat-mdc-action-list mat-mdc-list-base mdc-list",
        "role": "group"
      },
      encapsulation: ViewEncapsulation.None,
      changeDetection: ChangeDetectionStrategy.OnPush,
      providers: [{
        provide: MatListBase,
        useExisting: MatActionList
      }],
      styles: ['.mdc-list {\n  margin: 0;\n  padding: 8px 0;\n  list-style-type: none;\n}\n.mdc-list:focus {\n  outline: none;\n}\n\n.mdc-list-item {\n  display: flex;\n  position: relative;\n  justify-content: flex-start;\n  overflow: hidden;\n  padding: 0;\n  align-items: stretch;\n  cursor: pointer;\n  padding-left: 16px;\n  padding-right: 16px;\n  background-color: var(--mat-list-list-item-container-color, transparent);\n  border-radius: var(--mat-list-list-item-container-shape, var(--mat-sys-corner-none));\n}\n.mdc-list-item.mdc-list-item--selected {\n  background-color: var(--mat-list-list-item-selected-container-color);\n}\n.mdc-list-item:focus {\n  outline: 0;\n}\n.mdc-list-item.mdc-list-item--disabled {\n  cursor: auto;\n}\n.mdc-list-item.mdc-list-item--with-one-line {\n  height: var(--mat-list-list-item-one-line-container-height, 48px);\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__start {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-two-lines {\n  height: var(--mat-list-list-item-two-line-container-height, 64px);\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-three-lines {\n  height: var(--mat-list-list-item-three-line-container-height, 88px);\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--selected::before, .mdc-list-item.mdc-list-item--selected:focus::before, .mdc-list-item:not(.mdc-list-item--selected):focus::before {\n  position: absolute;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  content: "";\n  pointer-events: none;\n}\n\na.mdc-list-item {\n  color: inherit;\n  text-decoration: none;\n}\n\n.mdc-list-item__start {\n  fill: currentColor;\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-leading-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-leading-icon-size, 24px);\n  height: var(--mat-list-list-item-leading-icon-size, 24px);\n  margin-left: 16px;\n  margin-right: 32px;\n}\n[dir=rtl] .mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-left: 32px;\n  margin-right: 16px;\n}\n.mdc-list-item--with-leading-icon:hover .mdc-list-item__start {\n  color: var(--mat-list-list-item-hover-leading-icon-color);\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  width: var(--mat-list-list-item-leading-avatar-size, 40px);\n  height: var(--mat-list-list-item-leading-avatar-size, 40px);\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start, [dir=rtl] .mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n\n.mdc-list-item__end {\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  font-family: var(--mat-list-list-item-trailing-supporting-text-font, var(--mat-sys-label-small-font));\n  line-height: var(--mat-list-list-item-trailing-supporting-text-line-height, var(--mat-sys-label-small-line-height));\n  font-size: var(--mat-list-list-item-trailing-supporting-text-size, var(--mat-sys-label-small-size));\n  font-weight: var(--mat-list-list-item-trailing-supporting-text-weight, var(--mat-sys-label-small-weight));\n  letter-spacing: var(--mat-list-list-item-trailing-supporting-text-tracking, var(--mat-sys-label-small-tracking));\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-trailing-icon-size, 24px);\n  height: var(--mat-list-list-item-trailing-icon-size, 24px);\n}\n.mdc-list-item--with-trailing-icon:hover .mdc-list-item__end {\n  color: var(--mat-list-list-item-hover-trailing-icon-color);\n}\n.mdc-list-item.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-supporting-text-color, var(--mat-sys-on-surface-variant));\n}\n.mdc-list-item--selected.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-selected-trailing-icon-color, var(--mat-sys-primary));\n}\n\n.mdc-list-item__content {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  align-self: center;\n  flex: 1;\n  pointer-events: none;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__content, .mdc-list-item--with-three-lines .mdc-list-item__content {\n  align-self: stretch;\n}\n\n.mdc-list-item__primary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  color: var(--mat-list-list-item-label-text-color, var(--mat-sys-on-surface));\n  font-family: var(--mat-list-list-item-label-text-font, var(--mat-sys-body-large-font));\n  line-height: var(--mat-list-list-item-label-text-line-height, var(--mat-sys-body-large-line-height));\n  font-size: var(--mat-list-list-item-label-text-size, var(--mat-sys-body-large-size));\n  font-weight: var(--mat-list-list-item-label-text-weight, var(--mat-sys-body-large-weight));\n  letter-spacing: var(--mat-list-list-item-label-text-tracking, var(--mat-sys-body-large-tracking));\n}\n.mdc-list-item:hover .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-hover-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item:focus .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-focus-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text, .mdc-list-item--with-three-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n\n.mdc-list-item__secondary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  display: block;\n  margin-top: 0;\n  color: var(--mat-list-list-item-supporting-text-color, var(--mat-sys-on-surface-variant));\n  font-family: var(--mat-list-list-item-supporting-text-font, var(--mat-sys-body-medium-font));\n  line-height: var(--mat-list-list-item-supporting-text-line-height, var(--mat-sys-body-medium-line-height));\n  font-size: var(--mat-list-list-item-supporting-text-size, var(--mat-sys-body-medium-size));\n  font-weight: var(--mat-list-list-item-supporting-text-weight, var(--mat-sys-body-medium-weight));\n  letter-spacing: var(--mat-list-list-item-supporting-text-tracking, var(--mat-sys-body-medium-tracking));\n}\n.mdc-list-item__secondary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-three-lines .mdc-list-item__secondary-text {\n  white-space: normal;\n  line-height: 20px;\n}\n.mdc-list-item--with-overline .mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: auto;\n}\n\n.mdc-list-item--with-leading-radio.mdc-list-item,\n.mdc-list-item--with-leading-checkbox.mdc-list-item,\n.mdc-list-item--with-leading-icon.mdc-list-item,\n.mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-checkbox.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-icon.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-trailing-icon.mdc-list-item, [dir=rtl] .mdc-list-item--with-trailing-icon.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n}\n\n.mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  -webkit-user-select: none;\n  user-select: none;\n  margin-left: 28px;\n  margin-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 28px;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end {\n  display: block;\n  line-height: normal;\n  align-self: flex-start;\n  margin-top: 0;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end::before, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-leading-radio .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio .mdc-list-item__start,\n[dir=rtl] .mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-item--with-trailing-radio.mdc-list-item,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-left: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, [dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-radio .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio .mdc-list-item__end,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-three-lines .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-group__subheader {\n  margin: 0.75rem 16px;\n}\n\n.mdc-list-item--disabled .mdc-list-item__start,\n.mdc-list-item--disabled .mdc-list-item__content,\n.mdc-list-item--disabled .mdc-list-item__end {\n  opacity: 1;\n}\n.mdc-list-item--disabled .mdc-list-item__primary-text,\n.mdc-list-item--disabled .mdc-list-item__secondary-text {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n.mdc-list-item--disabled.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-disabled-leading-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-leading-icon-opacity, 0.38);\n}\n.mdc-list-item--disabled.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-disabled-trailing-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-trailing-icon-opacity, 0.38);\n}\n\n.mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing, [dir=rtl] .mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing {\n  padding-left: 0;\n  padding-right: 0;\n}\n\n.mdc-list-item.mdc-list-item--disabled .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-disabled-label-text-color, var(--mat-sys-on-surface));\n}\n\n.mdc-list-item:hover::before {\n  background-color: var(--mat-list-list-item-hover-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-hover-state-layer-opacity, var(--mat-sys-hover-state-layer-opacity));\n}\n\n.mdc-list-item.mdc-list-item--disabled::before {\n  background-color: var(--mat-list-list-item-disabled-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item:focus::before {\n  background-color: var(--mat-list-list-item-focus-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-focus-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item--disabled .mdc-radio,\n.mdc-list-item--disabled .mdc-checkbox {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n\n.mdc-list-item--with-leading-avatar .mat-mdc-list-item-avatar {\n  border-radius: var(--mat-list-list-item-leading-avatar-shape, var(--mat-sys-corner-full));\n  background-color: var(--mat-list-list-item-leading-avatar-color, var(--mat-sys-primary-container));\n}\n\n.mat-mdc-list-item-icon {\n  font-size: var(--mat-list-list-item-leading-icon-size, 24px);\n}\n\n@media (forced-colors: active) {\n  a.mdc-list-item--activated::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  a.mdc-list-item--activated [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n\n.mat-mdc-list-base {\n  display: block;\n}\n.mat-mdc-list-base .mdc-list-item__start,\n.mat-mdc-list-base .mdc-list-item__end,\n.mat-mdc-list-base .mdc-list-item__content {\n  pointer-events: auto;\n}\n\n.mat-mdc-list-item,\n.mat-mdc-list-option {\n  width: 100%;\n  box-sizing: border-box;\n  -webkit-tap-highlight-color: transparent;\n}\n.mat-mdc-list-item:not(.mat-mdc-list-item-interactive),\n.mat-mdc-list-option:not(.mat-mdc-list-item-interactive) {\n  cursor: default;\n}\n.mat-mdc-list-item .mat-divider-inset,\n.mat-mdc-list-option .mat-divider-inset {\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n.mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n.mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-left: 72px;\n}\n[dir=rtl] .mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n[dir=rtl] .mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-right: 72px;\n}\n\n.mat-mdc-list-item-interactive::before {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  content: "";\n  opacity: 0;\n  pointer-events: none;\n  border-radius: inherit;\n}\n\n.mat-mdc-list-item > .mat-focus-indicator {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  pointer-events: none;\n}\n.mat-mdc-list-item:focus-visible > .mat-focus-indicator::before {\n  content: "";\n}\n\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-line.mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: normal;\n}\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-unscoped-content.mdc-list-item__secondary-text {\n  display: -webkit-box;\n  -webkit-box-orient: vertical;\n  -webkit-line-clamp: 2;\n}\n\nmat-action-list button {\n  background: none;\n  color: inherit;\n  border: none;\n  font: inherit;\n  outline: inherit;\n  -webkit-tap-highlight-color: transparent;\n  text-align: start;\n}\nmat-action-list button::-moz-focus-inner {\n  border: 0;\n}\n\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-inline-start: var(--mat-list-list-item-leading-icon-start-space, 16px);\n  margin-inline-end: var(--mat-list-list-item-leading-icon-end-space, 16px);\n}\n\n.mat-mdc-nav-list .mat-mdc-list-item {\n  border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n  --mat-focus-indicator-border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n}\n.mat-mdc-nav-list .mat-mdc-list-item.mdc-list-item--activated {\n  background-color: var(--mat-list-active-indicator-color, var(--mat-sys-secondary-container));\n}\n']
    }]
  }], null, null);
})();
var MAT_LIST = new InjectionToken("MatList");
var MatList = class _MatList extends MatListBase {
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatList_BaseFactory;
    return function MatList_Factory(__ngFactoryType__) {
      return (ɵMatList_BaseFactory || (ɵMatList_BaseFactory = ɵɵgetInheritedFactory(_MatList)))(__ngFactoryType__ || _MatList);
    };
  })();
  static ɵcmp = ɵɵdefineComponent({
    type: _MatList,
    selectors: [["mat-list"]],
    hostAttrs: [1, "mat-mdc-list", "mat-mdc-list-base", "mdc-list"],
    exportAs: ["matList"],
    features: [ɵɵProvidersFeature([{
      provide: MatListBase,
      useExisting: _MatList
    }]), ɵɵInheritDefinitionFeature],
    ngContentSelectors: _c0,
    decls: 1,
    vars: 0,
    template: function MatList_Template(rf, ctx) {
      if (rf & 1) {
        ɵɵprojectionDef();
        ɵɵprojection(0);
      }
    },
    styles: [_c1],
    encapsulation: 2,
    changeDetection: 0
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatList, [{
    type: Component,
    args: [{
      selector: "mat-list",
      exportAs: "matList",
      template: "<ng-content></ng-content>",
      host: {
        "class": "mat-mdc-list mat-mdc-list-base mdc-list"
      },
      encapsulation: ViewEncapsulation.None,
      changeDetection: ChangeDetectionStrategy.OnPush,
      providers: [{
        provide: MatListBase,
        useExisting: MatList
      }],
      styles: ['.mdc-list {\n  margin: 0;\n  padding: 8px 0;\n  list-style-type: none;\n}\n.mdc-list:focus {\n  outline: none;\n}\n\n.mdc-list-item {\n  display: flex;\n  position: relative;\n  justify-content: flex-start;\n  overflow: hidden;\n  padding: 0;\n  align-items: stretch;\n  cursor: pointer;\n  padding-left: 16px;\n  padding-right: 16px;\n  background-color: var(--mat-list-list-item-container-color, transparent);\n  border-radius: var(--mat-list-list-item-container-shape, var(--mat-sys-corner-none));\n}\n.mdc-list-item.mdc-list-item--selected {\n  background-color: var(--mat-list-list-item-selected-container-color);\n}\n.mdc-list-item:focus {\n  outline: 0;\n}\n.mdc-list-item.mdc-list-item--disabled {\n  cursor: auto;\n}\n.mdc-list-item.mdc-list-item--with-one-line {\n  height: var(--mat-list-list-item-one-line-container-height, 48px);\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__start {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-two-lines {\n  height: var(--mat-list-list-item-two-line-container-height, 64px);\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-three-lines {\n  height: var(--mat-list-list-item-three-line-container-height, 88px);\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--selected::before, .mdc-list-item.mdc-list-item--selected:focus::before, .mdc-list-item:not(.mdc-list-item--selected):focus::before {\n  position: absolute;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  content: "";\n  pointer-events: none;\n}\n\na.mdc-list-item {\n  color: inherit;\n  text-decoration: none;\n}\n\n.mdc-list-item__start {\n  fill: currentColor;\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-leading-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-leading-icon-size, 24px);\n  height: var(--mat-list-list-item-leading-icon-size, 24px);\n  margin-left: 16px;\n  margin-right: 32px;\n}\n[dir=rtl] .mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-left: 32px;\n  margin-right: 16px;\n}\n.mdc-list-item--with-leading-icon:hover .mdc-list-item__start {\n  color: var(--mat-list-list-item-hover-leading-icon-color);\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  width: var(--mat-list-list-item-leading-avatar-size, 40px);\n  height: var(--mat-list-list-item-leading-avatar-size, 40px);\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start, [dir=rtl] .mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n\n.mdc-list-item__end {\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  font-family: var(--mat-list-list-item-trailing-supporting-text-font, var(--mat-sys-label-small-font));\n  line-height: var(--mat-list-list-item-trailing-supporting-text-line-height, var(--mat-sys-label-small-line-height));\n  font-size: var(--mat-list-list-item-trailing-supporting-text-size, var(--mat-sys-label-small-size));\n  font-weight: var(--mat-list-list-item-trailing-supporting-text-weight, var(--mat-sys-label-small-weight));\n  letter-spacing: var(--mat-list-list-item-trailing-supporting-text-tracking, var(--mat-sys-label-small-tracking));\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-trailing-icon-size, 24px);\n  height: var(--mat-list-list-item-trailing-icon-size, 24px);\n}\n.mdc-list-item--with-trailing-icon:hover .mdc-list-item__end {\n  color: var(--mat-list-list-item-hover-trailing-icon-color);\n}\n.mdc-list-item.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-supporting-text-color, var(--mat-sys-on-surface-variant));\n}\n.mdc-list-item--selected.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-selected-trailing-icon-color, var(--mat-sys-primary));\n}\n\n.mdc-list-item__content {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  align-self: center;\n  flex: 1;\n  pointer-events: none;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__content, .mdc-list-item--with-three-lines .mdc-list-item__content {\n  align-self: stretch;\n}\n\n.mdc-list-item__primary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  color: var(--mat-list-list-item-label-text-color, var(--mat-sys-on-surface));\n  font-family: var(--mat-list-list-item-label-text-font, var(--mat-sys-body-large-font));\n  line-height: var(--mat-list-list-item-label-text-line-height, var(--mat-sys-body-large-line-height));\n  font-size: var(--mat-list-list-item-label-text-size, var(--mat-sys-body-large-size));\n  font-weight: var(--mat-list-list-item-label-text-weight, var(--mat-sys-body-large-weight));\n  letter-spacing: var(--mat-list-list-item-label-text-tracking, var(--mat-sys-body-large-tracking));\n}\n.mdc-list-item:hover .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-hover-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item:focus .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-focus-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text, .mdc-list-item--with-three-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n\n.mdc-list-item__secondary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  display: block;\n  margin-top: 0;\n  color: var(--mat-list-list-item-supporting-text-color, var(--mat-sys-on-surface-variant));\n  font-family: var(--mat-list-list-item-supporting-text-font, var(--mat-sys-body-medium-font));\n  line-height: var(--mat-list-list-item-supporting-text-line-height, var(--mat-sys-body-medium-line-height));\n  font-size: var(--mat-list-list-item-supporting-text-size, var(--mat-sys-body-medium-size));\n  font-weight: var(--mat-list-list-item-supporting-text-weight, var(--mat-sys-body-medium-weight));\n  letter-spacing: var(--mat-list-list-item-supporting-text-tracking, var(--mat-sys-body-medium-tracking));\n}\n.mdc-list-item__secondary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-three-lines .mdc-list-item__secondary-text {\n  white-space: normal;\n  line-height: 20px;\n}\n.mdc-list-item--with-overline .mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: auto;\n}\n\n.mdc-list-item--with-leading-radio.mdc-list-item,\n.mdc-list-item--with-leading-checkbox.mdc-list-item,\n.mdc-list-item--with-leading-icon.mdc-list-item,\n.mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-checkbox.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-icon.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-trailing-icon.mdc-list-item, [dir=rtl] .mdc-list-item--with-trailing-icon.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n}\n\n.mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  -webkit-user-select: none;\n  user-select: none;\n  margin-left: 28px;\n  margin-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 28px;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end {\n  display: block;\n  line-height: normal;\n  align-self: flex-start;\n  margin-top: 0;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end::before, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-leading-radio .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio .mdc-list-item__start,\n[dir=rtl] .mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-item--with-trailing-radio.mdc-list-item,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-left: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, [dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-radio .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio .mdc-list-item__end,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-three-lines .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-group__subheader {\n  margin: 0.75rem 16px;\n}\n\n.mdc-list-item--disabled .mdc-list-item__start,\n.mdc-list-item--disabled .mdc-list-item__content,\n.mdc-list-item--disabled .mdc-list-item__end {\n  opacity: 1;\n}\n.mdc-list-item--disabled .mdc-list-item__primary-text,\n.mdc-list-item--disabled .mdc-list-item__secondary-text {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n.mdc-list-item--disabled.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-disabled-leading-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-leading-icon-opacity, 0.38);\n}\n.mdc-list-item--disabled.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-disabled-trailing-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-trailing-icon-opacity, 0.38);\n}\n\n.mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing, [dir=rtl] .mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing {\n  padding-left: 0;\n  padding-right: 0;\n}\n\n.mdc-list-item.mdc-list-item--disabled .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-disabled-label-text-color, var(--mat-sys-on-surface));\n}\n\n.mdc-list-item:hover::before {\n  background-color: var(--mat-list-list-item-hover-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-hover-state-layer-opacity, var(--mat-sys-hover-state-layer-opacity));\n}\n\n.mdc-list-item.mdc-list-item--disabled::before {\n  background-color: var(--mat-list-list-item-disabled-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item:focus::before {\n  background-color: var(--mat-list-list-item-focus-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-focus-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item--disabled .mdc-radio,\n.mdc-list-item--disabled .mdc-checkbox {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n\n.mdc-list-item--with-leading-avatar .mat-mdc-list-item-avatar {\n  border-radius: var(--mat-list-list-item-leading-avatar-shape, var(--mat-sys-corner-full));\n  background-color: var(--mat-list-list-item-leading-avatar-color, var(--mat-sys-primary-container));\n}\n\n.mat-mdc-list-item-icon {\n  font-size: var(--mat-list-list-item-leading-icon-size, 24px);\n}\n\n@media (forced-colors: active) {\n  a.mdc-list-item--activated::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  a.mdc-list-item--activated [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n\n.mat-mdc-list-base {\n  display: block;\n}\n.mat-mdc-list-base .mdc-list-item__start,\n.mat-mdc-list-base .mdc-list-item__end,\n.mat-mdc-list-base .mdc-list-item__content {\n  pointer-events: auto;\n}\n\n.mat-mdc-list-item,\n.mat-mdc-list-option {\n  width: 100%;\n  box-sizing: border-box;\n  -webkit-tap-highlight-color: transparent;\n}\n.mat-mdc-list-item:not(.mat-mdc-list-item-interactive),\n.mat-mdc-list-option:not(.mat-mdc-list-item-interactive) {\n  cursor: default;\n}\n.mat-mdc-list-item .mat-divider-inset,\n.mat-mdc-list-option .mat-divider-inset {\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n.mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n.mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-left: 72px;\n}\n[dir=rtl] .mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n[dir=rtl] .mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-right: 72px;\n}\n\n.mat-mdc-list-item-interactive::before {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  content: "";\n  opacity: 0;\n  pointer-events: none;\n  border-radius: inherit;\n}\n\n.mat-mdc-list-item > .mat-focus-indicator {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  pointer-events: none;\n}\n.mat-mdc-list-item:focus-visible > .mat-focus-indicator::before {\n  content: "";\n}\n\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-line.mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: normal;\n}\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-unscoped-content.mdc-list-item__secondary-text {\n  display: -webkit-box;\n  -webkit-box-orient: vertical;\n  -webkit-line-clamp: 2;\n}\n\nmat-action-list button {\n  background: none;\n  color: inherit;\n  border: none;\n  font: inherit;\n  outline: inherit;\n  -webkit-tap-highlight-color: transparent;\n  text-align: start;\n}\nmat-action-list button::-moz-focus-inner {\n  border: 0;\n}\n\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-inline-start: var(--mat-list-list-item-leading-icon-start-space, 16px);\n  margin-inline-end: var(--mat-list-list-item-leading-icon-end-space, 16px);\n}\n\n.mat-mdc-nav-list .mat-mdc-list-item {\n  border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n  --mat-focus-indicator-border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n}\n.mat-mdc-nav-list .mat-mdc-list-item.mdc-list-item--activated {\n  background-color: var(--mat-list-active-indicator-color, var(--mat-sys-secondary-container));\n}\n']
    }]
  }], null, null);
})();
var MatListItem = class _MatListItem extends MatListItemBase {
  _lines;
  _titles;
  _meta;
  _unscopedContent;
  _itemText;
  get activated() {
    return this._activated;
  }
  set activated(activated) {
    this._activated = coerceBooleanProperty(activated);
  }
  _activated = false;
  _getAriaCurrent() {
    return this._hostElement.nodeName === "A" && this._activated ? "page" : null;
  }
  _hasBothLeadingAndTrailing() {
    return this._meta.length !== 0 && (this._avatars.length !== 0 || this._icons.length !== 0);
  }
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatListItem_BaseFactory;
    return function MatListItem_Factory(__ngFactoryType__) {
      return (ɵMatListItem_BaseFactory || (ɵMatListItem_BaseFactory = ɵɵgetInheritedFactory(_MatListItem)))(__ngFactoryType__ || _MatListItem);
    };
  })();
  static ɵcmp = ɵɵdefineComponent({
    type: _MatListItem,
    selectors: [["mat-list-item"], ["a", "mat-list-item", ""], ["button", "mat-list-item", ""]],
    contentQueries: function MatListItem_ContentQueries(rf, ctx, dirIndex) {
      if (rf & 1) {
        ɵɵcontentQuery(dirIndex, MatListItemLine, 5)(dirIndex, MatListItemTitle, 5)(dirIndex, MatListItemMeta, 5);
      }
      if (rf & 2) {
        let _t;
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._lines = _t);
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._titles = _t);
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._meta = _t);
      }
    },
    viewQuery: function MatListItem_Query(rf, ctx) {
      if (rf & 1) {
        ɵɵviewQuery(_c2, 5)(_c3, 5);
      }
      if (rf & 2) {
        let _t;
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._unscopedContent = _t.first);
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._itemText = _t.first);
      }
    },
    hostAttrs: [1, "mat-mdc-list-item", "mdc-list-item"],
    hostVars: 13,
    hostBindings: function MatListItem_HostBindings(rf, ctx) {
      if (rf & 2) {
        ɵɵattribute("aria-current", ctx._getAriaCurrent());
        ɵɵclassProp("mdc-list-item--activated", ctx.activated)("mdc-list-item--with-leading-avatar", ctx._avatars.length !== 0)("mdc-list-item--with-leading-icon", ctx._icons.length !== 0)("mdc-list-item--with-trailing-meta", ctx._meta.length !== 0)("mat-mdc-list-item-both-leading-and-trailing", ctx._hasBothLeadingAndTrailing())("_mat-animation-noopable", ctx._noopAnimations);
      }
    },
    inputs: {
      activated: "activated"
    },
    exportAs: ["matListItem"],
    features: [ɵɵInheritDefinitionFeature],
    ngContentSelectors: _c5,
    decls: 10,
    vars: 0,
    consts: [["unscopedContent", ""], [1, "mdc-list-item__content"], [1, "mat-mdc-list-item-unscoped-content", 3, "cdkObserveContent"], [1, "mat-focus-indicator"]],
    template: function MatListItem_Template(rf, ctx) {
      if (rf & 1) {
        ɵɵprojectionDef(_c4);
        ɵɵprojection(0);
        ɵɵelementStart(1, "span", 1);
        ɵɵprojection(2, 1);
        ɵɵprojection(3, 2);
        ɵɵelementStart(4, "span", 2, 0);
        ɵɵlistener("cdkObserveContent", function MatListItem_Template_span_cdkObserveContent_4_listener() {
          return ctx._updateItemLines(true);
        });
        ɵɵprojection(6, 3);
        ɵɵelementEnd()();
        ɵɵprojection(7, 4);
        ɵɵprojection(8, 5);
        ɵɵelement(9, "div", 3);
      }
    },
    dependencies: [CdkObserveContent],
    encapsulation: 2,
    changeDetection: 0
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListItem, [{
    type: Component,
    args: [{
      selector: "mat-list-item, a[mat-list-item], button[mat-list-item]",
      exportAs: "matListItem",
      host: {
        "class": "mat-mdc-list-item mdc-list-item",
        "[class.mdc-list-item--activated]": "activated",
        "[class.mdc-list-item--with-leading-avatar]": "_avatars.length !== 0",
        "[class.mdc-list-item--with-leading-icon]": "_icons.length !== 0",
        "[class.mdc-list-item--with-trailing-meta]": "_meta.length !== 0",
        "[class.mat-mdc-list-item-both-leading-and-trailing]": "_hasBothLeadingAndTrailing()",
        "[class._mat-animation-noopable]": "_noopAnimations",
        "[attr.aria-current]": "_getAriaCurrent()"
      },
      encapsulation: ViewEncapsulation.None,
      changeDetection: ChangeDetectionStrategy.OnPush,
      imports: [CdkObserveContent],
      template: '<ng-content select="[matListItemAvatar],[matListItemIcon]"></ng-content>\n\n<span class="mdc-list-item__content">\n  <ng-content select="[matListItemTitle]"></ng-content>\n  <ng-content select="[matListItemLine]"></ng-content>\n  <span #unscopedContent class="mat-mdc-list-item-unscoped-content"\n        (cdkObserveContent)="_updateItemLines(true)">\n    <ng-content></ng-content>\n  </span>\n</span>\n\n<ng-content select="[matListItemMeta]"></ng-content>\n\n<ng-content select="mat-divider"></ng-content>\n\n<!--\n  Strong focus indicator element. MDC uses the `::before` pseudo element for the default\n  focus/hover/selected state, so we need a separate element.\n-->\n<div class="mat-focus-indicator"></div>\n'
    }]
  }], null, {
    _lines: [{
      type: ContentChildren,
      args: [MatListItemLine, {
        descendants: true
      }]
    }],
    _titles: [{
      type: ContentChildren,
      args: [MatListItemTitle, {
        descendants: true
      }]
    }],
    _meta: [{
      type: ContentChildren,
      args: [MatListItemMeta, {
        descendants: true
      }]
    }],
    _unscopedContent: [{
      type: ViewChild,
      args: ["unscopedContent"]
    }],
    _itemText: [{
      type: ViewChild,
      args: ["text"]
    }],
    activated: [{
      type: Input
    }]
  });
})();
var SELECTION_LIST = new InjectionToken("SelectionList");
var MatListOption = class _MatListOption extends MatListItemBase {
  _selectionList = inject(SELECTION_LIST);
  _changeDetectorRef = inject(ChangeDetectorRef);
  _lines;
  _titles;
  _unscopedContent;
  selectedChange = new EventEmitter();
  togglePosition = "after";
  get checkboxPosition() {
    return this.togglePosition;
  }
  set checkboxPosition(value) {
    this.togglePosition = value;
  }
  get color() {
    return this._color || this._selectionList.color;
  }
  set color(newValue) {
    this._color = newValue;
  }
  _color;
  get value() {
    return this._value;
  }
  set value(newValue) {
    if (this.selected && newValue !== this.value && this._inputsInitialized) {
      this.selected = false;
    }
    this._value = newValue;
  }
  _value;
  get selected() {
    return this._selectionList.selectedOptions.isSelected(this);
  }
  set selected(value) {
    const isSelected = coerceBooleanProperty(value);
    if (isSelected !== this._selected) {
      this._setSelected(isSelected);
      if (isSelected || this._selectionList.multiple) {
        this._selectionList._reportValueChange();
      }
    }
  }
  _selected = false;
  _inputsInitialized = false;
  ngOnInit() {
    const list = this._selectionList;
    if (list._value && list._value.some((value) => list.compareWith(this._value, value))) {
      this._setSelected(true);
    }
    const wasSelected = this._selected;
    Promise.resolve().then(() => {
      if (this._selected || wasSelected) {
        this.selected = true;
        this._changeDetectorRef.markForCheck();
      }
    });
    this._inputsInitialized = true;
  }
  ngOnDestroy() {
    super.ngOnDestroy();
    if (this.selected) {
      Promise.resolve().then(() => {
        this.selected = false;
      });
    }
  }
  toggle() {
    this.selected = !this.selected;
  }
  focus() {
    this._hostElement.focus();
  }
  getLabel() {
    const titleElement = this._titles?.get(0)?._elementRef.nativeElement;
    const labelEl = titleElement || this._unscopedContent?.nativeElement;
    return labelEl?.textContent || "";
  }
  _hasCheckboxAt(position) {
    return this._selectionList.multiple && this._getTogglePosition() === position;
  }
  _hasRadioAt(position) {
    return !this._selectionList.multiple && this._getTogglePosition() === position && !this._selectionList.hideSingleSelectionIndicator;
  }
  _hasIconsOrAvatarsAt(position) {
    return this._hasProjected("icons", position) || this._hasProjected("avatars", position);
  }
  _hasProjected(type, position) {
    return this._getTogglePosition() !== position && (type === "avatars" ? this._avatars.length !== 0 : this._icons.length !== 0);
  }
  _handleBlur() {
    this._selectionList._onTouched();
  }
  _getTogglePosition() {
    return this.togglePosition || "after";
  }
  _setSelected(selected) {
    if (selected === this._selected) {
      return false;
    }
    this._selected = selected;
    if (selected) {
      this._selectionList.selectedOptions.select(this);
    } else {
      this._selectionList.selectedOptions.deselect(this);
    }
    this.selectedChange.emit(selected);
    this._changeDetectorRef.markForCheck();
    return true;
  }
  _markForCheck() {
    this._changeDetectorRef.markForCheck();
  }
  _toggleOnInteraction() {
    if (!this.disabled) {
      if (this._selectionList.multiple) {
        this.selected = !this.selected;
        this._selectionList._emitChangeEvent([this]);
      } else if (!this.selected) {
        this.selected = true;
        this._selectionList._emitChangeEvent([this]);
      }
    }
  }
  _setTabindex(value) {
    this._hostElement.setAttribute("tabindex", value + "");
  }
  _hasBothLeadingAndTrailing() {
    const hasLeading = this._hasProjected("avatars", "before") || this._hasProjected("icons", "before") || this._hasCheckboxAt("before") || this._hasRadioAt("before");
    const hasTrailing = this._hasProjected("icons", "after") || this._hasProjected("avatars", "after") || this._hasCheckboxAt("after") || this._hasRadioAt("after");
    return hasLeading && hasTrailing;
  }
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatListOption_BaseFactory;
    return function MatListOption_Factory(__ngFactoryType__) {
      return (ɵMatListOption_BaseFactory || (ɵMatListOption_BaseFactory = ɵɵgetInheritedFactory(_MatListOption)))(__ngFactoryType__ || _MatListOption);
    };
  })();
  static ɵcmp = ɵɵdefineComponent({
    type: _MatListOption,
    selectors: [["mat-list-option"]],
    contentQueries: function MatListOption_ContentQueries(rf, ctx, dirIndex) {
      if (rf & 1) {
        ɵɵcontentQuery(dirIndex, MatListItemLine, 5)(dirIndex, MatListItemTitle, 5);
      }
      if (rf & 2) {
        let _t;
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._lines = _t);
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._titles = _t);
      }
    },
    viewQuery: function MatListOption_Query(rf, ctx) {
      if (rf & 1) {
        ɵɵviewQuery(_c2, 5);
      }
      if (rf & 2) {
        let _t;
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._unscopedContent = _t.first);
      }
    },
    hostAttrs: ["role", "option", 1, "mat-mdc-list-item", "mat-mdc-list-option", "mdc-list-item"],
    hostVars: 27,
    hostBindings: function MatListOption_HostBindings(rf, ctx) {
      if (rf & 1) {
        ɵɵlistener("blur", function MatListOption_blur_HostBindingHandler() {
          return ctx._handleBlur();
        })("click", function MatListOption_click_HostBindingHandler() {
          return ctx._toggleOnInteraction();
        });
      }
      if (rf & 2) {
        ɵɵattribute("aria-selected", ctx.selected);
        ɵɵclassProp("mdc-list-item--selected", ctx.selected && !ctx._selectionList.multiple && ctx._selectionList.hideSingleSelectionIndicator)("mdc-list-item--with-leading-avatar", ctx._hasProjected("avatars", "before"))("mdc-list-item--with-leading-icon", ctx._hasProjected("icons", "before"))("mdc-list-item--with-trailing-icon", ctx._hasProjected("icons", "after"))("mat-mdc-list-option-with-trailing-avatar", ctx._hasProjected("avatars", "after"))("mdc-list-item--with-leading-checkbox", ctx._hasCheckboxAt("before"))("mdc-list-item--with-trailing-checkbox", ctx._hasCheckboxAt("after"))("mdc-list-item--with-leading-radio", ctx._hasRadioAt("before"))("mdc-list-item--with-trailing-radio", ctx._hasRadioAt("after"))("mat-mdc-list-item-both-leading-and-trailing", ctx._hasBothLeadingAndTrailing())("mat-accent", ctx.color !== "primary" && ctx.color !== "warn")("mat-warn", ctx.color === "warn")("_mat-animation-noopable", ctx._noopAnimations);
      }
    },
    inputs: {
      togglePosition: "togglePosition",
      checkboxPosition: "checkboxPosition",
      color: "color",
      value: "value",
      selected: "selected"
    },
    outputs: {
      selectedChange: "selectedChange"
    },
    exportAs: ["matListOption"],
    features: [ɵɵProvidersFeature([{
      provide: MatListItemBase,
      useExisting: _MatListOption
    }, {
      provide: LIST_OPTION,
      useExisting: _MatListOption
    }]), ɵɵInheritDefinitionFeature],
    ngContentSelectors: _c7,
    decls: 20,
    vars: 4,
    consts: [["icons", ""], ["checkbox", ""], ["radio", ""], ["unscopedContent", ""], [1, "mdc-list-item__start", "mat-mdc-list-option-checkbox-before"], [1, "mdc-list-item__start", "mat-mdc-list-option-radio-before"], [3, "ngTemplateOutlet"], [1, "mdc-list-item__content"], [1, "mat-mdc-list-item-unscoped-content", 3, "cdkObserveContent"], [1, "mdc-list-item__end"], [1, "mat-focus-indicator"], [1, "mdc-checkbox"], ["type", "checkbox", 1, "mdc-checkbox__native-control", 3, "checked", "disabled"], [1, "mdc-checkbox__background"], ["viewBox", "0 0 24 24", "aria-hidden", "true", 1, "mdc-checkbox__checkmark"], ["fill", "none", "d", "M1.73,12.91 8.1,19.28 22.79,4.59", 1, "mdc-checkbox__checkmark-path"], [1, "mdc-checkbox__mixedmark"], [1, "mdc-radio"], ["type", "radio", 1, "mdc-radio__native-control", 3, "checked", "disabled"], [1, "mdc-radio__background"], [1, "mdc-radio__outer-circle"], [1, "mdc-radio__inner-circle"]],
    template: function MatListOption_Template(rf, ctx) {
      if (rf & 1) {
        ɵɵprojectionDef(_c6);
        ɵɵtemplate(0, MatListOption_ng_template_0_Template, 1, 0, "ng-template", null, 0, ɵɵtemplateRefExtractor)(2, MatListOption_ng_template_2_Template, 6, 4, "ng-template", null, 1, ɵɵtemplateRefExtractor)(4, MatListOption_ng_template_4_Template, 5, 4, "ng-template", null, 2, ɵɵtemplateRefExtractor);
        ɵɵconditionalCreate(6, MatListOption_Conditional_6_Template, 2, 1, "span", 4)(7, MatListOption_Conditional_7_Template, 2, 1, "span", 5);
        ɵɵconditionalCreate(8, MatListOption_Conditional_8_Template, 1, 1, null, 6);
        ɵɵelementStart(9, "span", 7);
        ɵɵprojection(10);
        ɵɵprojection(11, 1);
        ɵɵelementStart(12, "span", 8, 3);
        ɵɵlistener("cdkObserveContent", function MatListOption_Template_span_cdkObserveContent_12_listener() {
          return ctx._updateItemLines(true);
        });
        ɵɵprojection(14, 2);
        ɵɵelementEnd()();
        ɵɵconditionalCreate(15, MatListOption_Conditional_15_Template, 2, 1, "span", 9)(16, MatListOption_Conditional_16_Template, 2, 1, "span", 9);
        ɵɵconditionalCreate(17, MatListOption_Conditional_17_Template, 1, 1, null, 6);
        ɵɵprojection(18, 3);
        ɵɵelement(19, "div", 10);
      }
      if (rf & 2) {
        ɵɵadvance(6);
        ɵɵconditional(ctx._hasCheckboxAt("before") ? 6 : ctx._hasRadioAt("before") ? 7 : -1);
        ɵɵadvance(2);
        ɵɵconditional(ctx._hasIconsOrAvatarsAt("before") ? 8 : -1);
        ɵɵadvance(7);
        ɵɵconditional(ctx._hasCheckboxAt("after") ? 15 : ctx._hasRadioAt("after") ? 16 : -1);
        ɵɵadvance(2);
        ɵɵconditional(ctx._hasIconsOrAvatarsAt("after") ? 17 : -1);
      }
    },
    dependencies: [NgTemplateOutlet, CdkObserveContent],
    styles: ['.mat-mdc-list-option-with-trailing-avatar.mdc-list-item, [dir=rtl] .mat-mdc-list-option-with-trailing-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mat-mdc-list-option-with-trailing-avatar .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n  width: 40px;\n  height: 40px;\n}\n.mat-mdc-list-option-with-trailing-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mat-mdc-list-option-with-trailing-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mat-mdc-list-option-with-trailing-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mat-mdc-list-option-with-trailing-avatar .mdc-list-item__end {\n  border-radius: 50%;\n}\n\n.mat-mdc-list-option .mdc-checkbox {\n  display: inline-block;\n  position: relative;\n  flex: 0 0 18px;\n  box-sizing: content-box;\n  width: 18px;\n  height: 18px;\n  line-height: 0;\n  white-space: nowrap;\n  cursor: pointer;\n  vertical-align: bottom;\n  padding: calc((var(--mat-checkbox-state-layer-size, 40px) - 18px) / 2);\n  margin: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n}\n.mat-mdc-list-option .mdc-checkbox .mdc-checkbox__native-control {\n  position: absolute;\n  margin: 0;\n  padding: 0;\n  opacity: 0;\n  cursor: inherit;\n  z-index: 1;\n  width: var(--mat-checkbox-state-layer-size, 40px);\n  height: var(--mat-checkbox-state-layer-size, 40px);\n  top: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n  right: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n  left: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n}\n.mat-mdc-list-option .mdc-checkbox--disabled {\n  cursor: default;\n  pointer-events: none;\n}\n.mat-mdc-list-option .mdc-checkbox__background {\n  display: inline-flex;\n  position: absolute;\n  align-items: center;\n  justify-content: center;\n  box-sizing: border-box;\n  width: 18px;\n  height: 18px;\n  border: 2px solid currentColor;\n  border-radius: 2px;\n  background-color: transparent;\n  pointer-events: none;\n  will-change: background-color, border-color;\n  transition: background-color 90ms cubic-bezier(0.4, 0, 0.6, 1), border-color 90ms cubic-bezier(0.4, 0, 0.6, 1);\n  -webkit-print-color-adjust: exact;\n  color-adjust: exact;\n  border-color: var(--mat-checkbox-unselected-icon-color, var(--mat-sys-on-surface-variant));\n  top: calc((var(--mat-checkbox-state-layer-size, 40px) - 18px) / 2);\n  left: calc((var(--mat-checkbox-state-layer-size, 40px) - 18px) / 2);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:enabled:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:enabled:indeterminate ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-selected-icon-color, var(--mat-sys-primary));\n  background-color: var(--mat-checkbox-selected-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-disabled-unselected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__background {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:disabled:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:disabled:indeterminate ~ .mdc-checkbox__background {\n  background-color: var(--mat-checkbox-disabled-selected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n  border-color: transparent;\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox__native-control:disabled:checked ~ .mdc-checkbox__background,\n  .mat-mdc-list-option .mdc-checkbox__native-control:disabled:indeterminate ~ .mdc-checkbox__background {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:not(:checked) ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:not(:indeterminate) ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-unselected-hover-icon-color, var(--mat-sys-on-surface));\n  background-color: transparent;\n}\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-selected-hover-icon-color, var(--mat-sys-primary));\n  background-color: var(--mat-checkbox-selected-hover-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:not(:checked) ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:not(:indeterminate) ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-unselected-focus-icon-color, var(--mat-sys-on-surface));\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:indeterminate ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-selected-focus-icon-color, var(--mat-sys-primary));\n  background-color: var(--mat-checkbox-selected-focus-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox:hover > .mdc-checkbox__native-control ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox .mdc-checkbox__native-control:focus ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-disabled-unselected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox:hover > .mdc-checkbox__native-control ~ .mdc-checkbox__background,\n  .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox .mdc-checkbox__native-control:focus ~ .mdc-checkbox__background,\n  .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__background {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background {\n  background-color: var(--mat-checkbox-disabled-selected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n  border-color: transparent;\n}\n.mat-mdc-list-option .mdc-checkbox__checkmark {\n  position: absolute;\n  top: 0;\n  right: 0;\n  bottom: 0;\n  left: 0;\n  width: 100%;\n  opacity: 0;\n  transition: opacity 180ms cubic-bezier(0.4, 0, 0.6, 1);\n  color: var(--mat-checkbox-selected-checkmark-color, var(--mat-sys-on-primary));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox__checkmark {\n    color: CanvasText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__checkmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__checkmark {\n  color: var(--mat-checkbox-disabled-selected-checkmark-color, var(--mat-sys-surface));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__checkmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__checkmark {\n    color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox__checkmark-path {\n  transition: stroke-dashoffset 180ms cubic-bezier(0.4, 0, 0.6, 1);\n  stroke: currentColor;\n  stroke-width: 3.12px;\n  stroke-dashoffset: 29.7833385;\n  stroke-dasharray: 29.7833385;\n}\n.mat-mdc-list-option .mdc-checkbox__mixedmark {\n  width: 100%;\n  height: 0;\n  transform: scaleX(0) rotate(0deg);\n  border-width: 1px;\n  border-style: solid;\n  opacity: 0;\n  transition: opacity 90ms cubic-bezier(0.4, 0, 0.6, 1), transform 90ms cubic-bezier(0.4, 0, 0.6, 1);\n  border-color: var(--mat-checkbox-selected-checkmark-color, var(--mat-sys-on-primary));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox__mixedmark {\n    margin: 0 1px;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__mixedmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__mixedmark {\n  border-color: var(--mat-checkbox-disabled-selected-checkmark-color, var(--mat-sys-surface));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__mixedmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__mixedmark {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-checked .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-indeterminate .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--anim-checked-unchecked .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-unchecked .mdc-checkbox__background {\n  animation-duration: 180ms;\n  animation-timing-function: linear;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-checked .mdc-checkbox__checkmark-path {\n  animation: mdc-checkbox-unchecked-checked-checkmark-path 180ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-indeterminate .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-unchecked-indeterminate-mixedmark 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-checked-unchecked .mdc-checkbox__checkmark-path {\n  animation: mdc-checkbox-checked-unchecked-checkmark-path 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-checked-indeterminate .mdc-checkbox__checkmark {\n  animation: mdc-checkbox-checked-indeterminate-checkmark 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-checked-indeterminate .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-checked-indeterminate-mixedmark 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-checked .mdc-checkbox__checkmark {\n  animation: mdc-checkbox-indeterminate-checked-checkmark 500ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-checked .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-indeterminate-checked-mixedmark 500ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-unchecked .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-indeterminate-unchecked-mixedmark 300ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background {\n  transition: border-color 90ms cubic-bezier(0, 0, 0.2, 1), background-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path,\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path {\n  stroke-dashoffset: 0;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background > .mdc-checkbox__checkmark {\n  transition: opacity 180ms cubic-bezier(0, 0, 0.2, 1), transform 180ms cubic-bezier(0, 0, 0.2, 1);\n  opacity: 1;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background > .mdc-checkbox__mixedmark {\n  transform: scaleX(1) rotate(-45deg);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background > .mdc-checkbox__checkmark {\n  transform: rotate(45deg);\n  opacity: 0;\n  transition: opacity 90ms cubic-bezier(0.4, 0, 0.6, 1), transform 90ms cubic-bezier(0.4, 0, 0.6, 1);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background > .mdc-checkbox__mixedmark {\n  transform: scaleX(1) rotate(0deg);\n  opacity: 1;\n}\n@keyframes mdc-checkbox-unchecked-checked-checkmark-path {\n  0%, 50% {\n    stroke-dashoffset: 29.7833385;\n  }\n  50% {\n    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);\n  }\n  100% {\n    stroke-dashoffset: 0;\n  }\n}\n@keyframes mdc-checkbox-unchecked-indeterminate-mixedmark {\n  0%, 68.2% {\n    transform: scaleX(0);\n  }\n  68.2% {\n    animation-timing-function: cubic-bezier(0, 0, 0, 1);\n  }\n  100% {\n    transform: scaleX(1);\n  }\n}\n@keyframes mdc-checkbox-checked-unchecked-checkmark-path {\n  from {\n    animation-timing-function: cubic-bezier(0.4, 0, 1, 1);\n    opacity: 1;\n    stroke-dashoffset: 0;\n  }\n  to {\n    opacity: 0;\n    stroke-dashoffset: -29.7833385;\n  }\n}\n@keyframes mdc-checkbox-checked-indeterminate-checkmark {\n  from {\n    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);\n    transform: rotate(0deg);\n    opacity: 1;\n  }\n  to {\n    transform: rotate(45deg);\n    opacity: 0;\n  }\n}\n@keyframes mdc-checkbox-indeterminate-checked-checkmark {\n  from {\n    animation-timing-function: cubic-bezier(0.14, 0, 0, 1);\n    transform: rotate(45deg);\n    opacity: 0;\n  }\n  to {\n    transform: rotate(360deg);\n    opacity: 1;\n  }\n}\n@keyframes mdc-checkbox-checked-indeterminate-mixedmark {\n  from {\n    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);\n    transform: rotate(-45deg);\n    opacity: 0;\n  }\n  to {\n    transform: rotate(0deg);\n    opacity: 1;\n  }\n}\n@keyframes mdc-checkbox-indeterminate-checked-mixedmark {\n  from {\n    animation-timing-function: cubic-bezier(0.14, 0, 0, 1);\n    transform: rotate(0deg);\n    opacity: 1;\n  }\n  to {\n    transform: rotate(315deg);\n    opacity: 0;\n  }\n}\n@keyframes mdc-checkbox-indeterminate-unchecked-mixedmark {\n  0% {\n    animation-timing-function: linear;\n    transform: scaleX(1);\n    opacity: 1;\n  }\n  32.8%, 100% {\n    transform: scaleX(0);\n    opacity: 0;\n  }\n}\n.mat-mdc-list-option .mdc-radio {\n  display: inline-block;\n  position: relative;\n  flex: 0 0 auto;\n  box-sizing: content-box;\n  width: 20px;\n  height: 20px;\n  cursor: pointer;\n  will-change: opacity, transform, border-color, color;\n  padding: calc((var(--mat-radio-state-layer-size, 40px) - 20px) / 2);\n}\n.mat-mdc-list-option .mdc-radio__background {\n  display: inline-block;\n  position: relative;\n  box-sizing: border-box;\n  width: 20px;\n  height: 20px;\n}\n.mat-mdc-list-option .mdc-radio__background::before {\n  position: absolute;\n  transform: scale(0, 0);\n  border-radius: 50%;\n  opacity: 0;\n  pointer-events: none;\n  content: "";\n  transition: opacity 90ms cubic-bezier(0.4, 0, 0.6, 1), transform 90ms cubic-bezier(0.4, 0, 0.6, 1);\n  width: var(--mat-radio-state-layer-size, 40px);\n  height: var(--mat-radio-state-layer-size, 40px);\n  top: calc(-1 * (var(--mat-radio-state-layer-size, 40px) - 20px) / 2);\n  left: calc(-1 * (var(--mat-radio-state-layer-size, 40px) - 20px) / 2);\n}\n.mat-mdc-list-option .mdc-radio__outer-circle {\n  position: absolute;\n  top: 0;\n  left: 0;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  border-width: 2px;\n  border-style: solid;\n  border-radius: 50%;\n  transition: border-color 90ms cubic-bezier(0.4, 0, 0.6, 1);\n}\n.mat-mdc-list-option .mdc-radio__inner-circle {\n  position: absolute;\n  top: 0;\n  left: 0;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  transform: scale(0);\n  border-radius: 50%;\n  transition: transform 90ms cubic-bezier(0.4, 0, 0.6, 1), background-color 90ms cubic-bezier(0.4, 0, 0.6, 1);\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-radio__inner-circle {\n    background-color: CanvasText !important;\n  }\n}\n.mat-mdc-list-option .mdc-radio__native-control {\n  position: absolute;\n  margin: 0;\n  padding: 0;\n  opacity: 0;\n  top: 0;\n  right: 0;\n  left: 0;\n  cursor: inherit;\n  z-index: 1;\n  width: var(--mat-radio-state-layer-size, 40px);\n  height: var(--mat-radio-state-layer-size, 40px);\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background, .mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background {\n  transition: opacity 90ms cubic-bezier(0, 0, 0.2, 1), transform 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background > .mdc-radio__outer-circle, .mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__outer-circle {\n  transition: border-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background > .mdc-radio__inner-circle, .mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__inner-circle {\n  transition: transform 90ms cubic-bezier(0, 0, 0.2, 1), background-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled:not(:checked) + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-disabled-unselected-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-radio-disabled-unselected-icon-opacity, 0.38);\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background {\n  cursor: default;\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-disabled-selected-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-radio-disabled-selected-icon-opacity, 0.38);\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__inner-circle {\n  background-color: var(--mat-radio-disabled-selected-icon-color, var(--mat-sys-on-surface, currentColor));\n  opacity: var(--mat-radio-disabled-selected-icon-opacity, 0.38);\n}\n.mat-mdc-list-option .mdc-radio__native-control:enabled:not(:checked) + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-unselected-icon-color, var(--mat-sys-on-surface-variant));\n}\n.mat-mdc-list-option .mdc-radio__native-control:enabled:checked + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-selected-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-radio__native-control:enabled:checked + .mdc-radio__background > .mdc-radio__inner-circle {\n  background-color: var(--mat-radio-selected-icon-color, var(--mat-sys-primary, currentColor));\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background > .mdc-radio__inner-circle {\n  transform: scale(0.5);\n  transition: transform 90ms cubic-bezier(0, 0, 0.2, 1), background-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option._mat-animation-noopable .mdc-radio__background::before,\n.mat-mdc-list-option._mat-animation-noopable .mdc-radio__outer-circle,\n.mat-mdc-list-option._mat-animation-noopable .mdc-radio__inner-circle {\n  transition: none !important;\n}\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mat-mdc-checkbox-touch-target,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__native-control,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__ripple,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mat-mdc-checkbox-ripple::before,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__mixedmark, .mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mat-mdc-checkbox-touch-target,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__native-control,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__ripple,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mat-mdc-checkbox-ripple::before,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__mixedmark {\n  transition: none !important;\n  animation: none !important;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control, .mat-mdc-list-option .mdc-radio__native-control {\n  display: none;\n}\n\n@media (forced-colors: active) {\n  .mat-mdc-list-option.mdc-list-item--selected::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  .mat-mdc-list-option.mdc-list-item--selected [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n'],
    encapsulation: 2,
    changeDetection: 0
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListOption, [{
    type: Component,
    args: [{
      selector: "mat-list-option",
      exportAs: "matListOption",
      host: {
        "class": "mat-mdc-list-item mat-mdc-list-option mdc-list-item",
        "role": "option",
        "[class.mdc-list-item--selected]": "selected && !_selectionList.multiple && _selectionList.hideSingleSelectionIndicator",
        "[class.mdc-list-item--with-leading-avatar]": '_hasProjected("avatars", "before")',
        "[class.mdc-list-item--with-leading-icon]": '_hasProjected("icons", "before")',
        "[class.mdc-list-item--with-trailing-icon]": '_hasProjected("icons", "after")',
        "[class.mat-mdc-list-option-with-trailing-avatar]": '_hasProjected("avatars", "after")',
        "[class.mdc-list-item--with-leading-checkbox]": '_hasCheckboxAt("before")',
        "[class.mdc-list-item--with-trailing-checkbox]": '_hasCheckboxAt("after")',
        "[class.mdc-list-item--with-leading-radio]": '_hasRadioAt("before")',
        "[class.mdc-list-item--with-trailing-radio]": '_hasRadioAt("after")',
        "[class.mat-mdc-list-item-both-leading-and-trailing]": "_hasBothLeadingAndTrailing()",
        "[class.mat-accent]": 'color !== "primary" && color !== "warn"',
        "[class.mat-warn]": 'color === "warn"',
        "[class._mat-animation-noopable]": "_noopAnimations",
        "[attr.aria-selected]": "selected",
        "(blur)": "_handleBlur()",
        "(click)": "_toggleOnInteraction()"
      },
      encapsulation: ViewEncapsulation.None,
      changeDetection: ChangeDetectionStrategy.OnPush,
      providers: [{
        provide: MatListItemBase,
        useExisting: MatListOption
      }, {
        provide: LIST_OPTION,
        useExisting: MatListOption
      }],
      imports: [NgTemplateOutlet, CdkObserveContent],
      template: `<!--
  Save icons and the pseudo checkbox/radio so that they can be re-used in the template without
  duplication. Also content can only be injected once so we need to extract icons/avatars
  into a template since we use it in multiple places.
-->
<ng-template #icons>
  <ng-content select="[matListItemAvatar],[matListItemIcon]">
  </ng-content>
</ng-template>

<ng-template #checkbox>
  <div class="mdc-checkbox" [class.mdc-checkbox--disabled]="disabled">
    <input type="checkbox" class="mdc-checkbox__native-control"
           [checked]="selected" [disabled]="disabled"/>
    <div class="mdc-checkbox__background">
      <svg class="mdc-checkbox__checkmark"
           viewBox="0 0 24 24"
           aria-hidden="true">
        <path class="mdc-checkbox__checkmark-path"
              fill="none"
              d="M1.73,12.91 8.1,19.28 22.79,4.59"/>
      </svg>
      <div class="mdc-checkbox__mixedmark"></div>
    </div>
  </div>
</ng-template>

<ng-template #radio>
  <div class="mdc-radio" [class.mdc-radio--disabled]="disabled">
    <input type="radio" class="mdc-radio__native-control"
           [checked]="selected" [disabled]="disabled"/>
    <div class="mdc-radio__background">
      <div class="mdc-radio__outer-circle"></div>
      <div class="mdc-radio__inner-circle"></div>
    </div>
  </div>
</ng-template>

@if (_hasCheckboxAt('before')) {
  <!-- Container for the checkbox at start. -->
  <span class="mdc-list-item__start mat-mdc-list-option-checkbox-before">
    <ng-template [ngTemplateOutlet]="checkbox"></ng-template>
  </span>
} @else if (_hasRadioAt('before')) {
  <!-- Container for the radio at the start. -->
  <span class="mdc-list-item__start mat-mdc-list-option-radio-before">
    <ng-template [ngTemplateOutlet]="radio"></ng-template>
  </span>
}
<!-- Conditionally renders icons/avatars before the list item text. -->
@if (_hasIconsOrAvatarsAt('before')) {
  <ng-template [ngTemplateOutlet]="icons"></ng-template>
}

<!-- Text -->
<span class="mdc-list-item__content">
  <ng-content select="[matListItemTitle]"></ng-content>
  <ng-content select="[matListItemLine]"></ng-content>
  <span #unscopedContent class="mat-mdc-list-item-unscoped-content"
        (cdkObserveContent)="_updateItemLines(true)">
    <ng-content></ng-content>
  </span>
</span>

@if (_hasCheckboxAt('after')) {
  <!-- Container for the checkbox at the end. -->
  <span class="mdc-list-item__end">
    <ng-template [ngTemplateOutlet]="checkbox"></ng-template>
  </span>
} @else if (_hasRadioAt('after')) {
  <!-- Container for the radio at the end. -->
  <span class="mdc-list-item__end">
    <ng-template [ngTemplateOutlet]="radio"></ng-template>
  </span>
}

<!-- Conditionally renders icons/avatars after the list item text. -->
@if (_hasIconsOrAvatarsAt('after')) {
  <ng-template [ngTemplateOutlet]="icons"></ng-template>
}

<!-- Divider -->
<ng-content select="mat-divider"></ng-content>

<!--
  Strong focus indicator element. MDC uses the \`::before\` pseudo element for the default
  focus/hover/selected state, so we need a separate element.
-->
<div class="mat-focus-indicator"></div>
`,
      styles: ['.mat-mdc-list-option-with-trailing-avatar.mdc-list-item, [dir=rtl] .mat-mdc-list-option-with-trailing-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mat-mdc-list-option-with-trailing-avatar .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n  width: 40px;\n  height: 40px;\n}\n.mat-mdc-list-option-with-trailing-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mat-mdc-list-option-with-trailing-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mat-mdc-list-option-with-trailing-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mat-mdc-list-option-with-trailing-avatar .mdc-list-item__end {\n  border-radius: 50%;\n}\n\n.mat-mdc-list-option .mdc-checkbox {\n  display: inline-block;\n  position: relative;\n  flex: 0 0 18px;\n  box-sizing: content-box;\n  width: 18px;\n  height: 18px;\n  line-height: 0;\n  white-space: nowrap;\n  cursor: pointer;\n  vertical-align: bottom;\n  padding: calc((var(--mat-checkbox-state-layer-size, 40px) - 18px) / 2);\n  margin: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n}\n.mat-mdc-list-option .mdc-checkbox .mdc-checkbox__native-control {\n  position: absolute;\n  margin: 0;\n  padding: 0;\n  opacity: 0;\n  cursor: inherit;\n  z-index: 1;\n  width: var(--mat-checkbox-state-layer-size, 40px);\n  height: var(--mat-checkbox-state-layer-size, 40px);\n  top: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n  right: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n  left: calc((var(--mat-checkbox-state-layer-size, 40px) - var(--mat-checkbox-state-layer-size, 40px)) / 2);\n}\n.mat-mdc-list-option .mdc-checkbox--disabled {\n  cursor: default;\n  pointer-events: none;\n}\n.mat-mdc-list-option .mdc-checkbox__background {\n  display: inline-flex;\n  position: absolute;\n  align-items: center;\n  justify-content: center;\n  box-sizing: border-box;\n  width: 18px;\n  height: 18px;\n  border: 2px solid currentColor;\n  border-radius: 2px;\n  background-color: transparent;\n  pointer-events: none;\n  will-change: background-color, border-color;\n  transition: background-color 90ms cubic-bezier(0.4, 0, 0.6, 1), border-color 90ms cubic-bezier(0.4, 0, 0.6, 1);\n  -webkit-print-color-adjust: exact;\n  color-adjust: exact;\n  border-color: var(--mat-checkbox-unselected-icon-color, var(--mat-sys-on-surface-variant));\n  top: calc((var(--mat-checkbox-state-layer-size, 40px) - 18px) / 2);\n  left: calc((var(--mat-checkbox-state-layer-size, 40px) - 18px) / 2);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:enabled:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:enabled:indeterminate ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-selected-icon-color, var(--mat-sys-primary));\n  background-color: var(--mat-checkbox-selected-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-disabled-unselected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__background {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:disabled:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:disabled:indeterminate ~ .mdc-checkbox__background {\n  background-color: var(--mat-checkbox-disabled-selected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n  border-color: transparent;\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox__native-control:disabled:checked ~ .mdc-checkbox__background,\n  .mat-mdc-list-option .mdc-checkbox__native-control:disabled:indeterminate ~ .mdc-checkbox__background {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:not(:checked) ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:not(:indeterminate) ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-unselected-hover-icon-color, var(--mat-sys-on-surface));\n  background-color: transparent;\n}\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox:hover > .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-selected-hover-icon-color, var(--mat-sys-primary));\n  background-color: var(--mat-checkbox-selected-hover-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:not(:checked) ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:not(:indeterminate) ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-unselected-focus-icon-color, var(--mat-sys-on-surface));\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:focus:focus:indeterminate ~ .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-selected-focus-icon-color, var(--mat-sys-primary));\n  background-color: var(--mat-checkbox-selected-focus-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox:hover > .mdc-checkbox__native-control ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox .mdc-checkbox__native-control:focus ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__background {\n  border-color: var(--mat-checkbox-disabled-unselected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox:hover > .mdc-checkbox__native-control ~ .mdc-checkbox__background,\n  .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox .mdc-checkbox__native-control:focus ~ .mdc-checkbox__background,\n  .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__background {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background {\n  background-color: var(--mat-checkbox-disabled-selected-icon-color, color-mix(in srgb, var(--mat-sys-on-surface) 38%, transparent));\n  border-color: transparent;\n}\n.mat-mdc-list-option .mdc-checkbox__checkmark {\n  position: absolute;\n  top: 0;\n  right: 0;\n  bottom: 0;\n  left: 0;\n  width: 100%;\n  opacity: 0;\n  transition: opacity 180ms cubic-bezier(0.4, 0, 0.6, 1);\n  color: var(--mat-checkbox-selected-checkmark-color, var(--mat-sys-on-primary));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox__checkmark {\n    color: CanvasText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__checkmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__checkmark {\n  color: var(--mat-checkbox-disabled-selected-checkmark-color, var(--mat-sys-surface));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__checkmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__checkmark {\n    color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox__checkmark-path {\n  transition: stroke-dashoffset 180ms cubic-bezier(0.4, 0, 0.6, 1);\n  stroke: currentColor;\n  stroke-width: 3.12px;\n  stroke-dashoffset: 29.7833385;\n  stroke-dasharray: 29.7833385;\n}\n.mat-mdc-list-option .mdc-checkbox__mixedmark {\n  width: 100%;\n  height: 0;\n  transform: scaleX(0) rotate(0deg);\n  border-width: 1px;\n  border-style: solid;\n  opacity: 0;\n  transition: opacity 90ms cubic-bezier(0.4, 0, 0.6, 1), transform 90ms cubic-bezier(0.4, 0, 0.6, 1);\n  border-color: var(--mat-checkbox-selected-checkmark-color, var(--mat-sys-on-primary));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox__mixedmark {\n    margin: 0 1px;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__mixedmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__mixedmark {\n  border-color: var(--mat-checkbox-disabled-selected-checkmark-color, var(--mat-sys-surface));\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-checkbox--disabled .mdc-checkbox__mixedmark, .mat-mdc-list-option .mdc-checkbox--disabled.mat-mdc-checkbox-disabled-interactive .mdc-checkbox__mixedmark {\n    border-color: GrayText;\n  }\n}\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-checked .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-indeterminate .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--anim-checked-unchecked .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-unchecked .mdc-checkbox__background {\n  animation-duration: 180ms;\n  animation-timing-function: linear;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-checked .mdc-checkbox__checkmark-path {\n  animation: mdc-checkbox-unchecked-checked-checkmark-path 180ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-unchecked-indeterminate .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-unchecked-indeterminate-mixedmark 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-checked-unchecked .mdc-checkbox__checkmark-path {\n  animation: mdc-checkbox-checked-unchecked-checkmark-path 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-checked-indeterminate .mdc-checkbox__checkmark {\n  animation: mdc-checkbox-checked-indeterminate-checkmark 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-checked-indeterminate .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-checked-indeterminate-mixedmark 90ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-checked .mdc-checkbox__checkmark {\n  animation: mdc-checkbox-indeterminate-checked-checkmark 500ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-checked .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-indeterminate-checked-mixedmark 500ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox--anim-indeterminate-unchecked .mdc-checkbox__mixedmark {\n  animation: mdc-checkbox-indeterminate-unchecked-mixedmark 300ms linear;\n  transition: none;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background,\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background {\n  transition: border-color 90ms cubic-bezier(0, 0, 0.2, 1), background-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path,\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path {\n  stroke-dashoffset: 0;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background > .mdc-checkbox__checkmark {\n  transition: opacity 180ms cubic-bezier(0, 0, 0.2, 1), transform 180ms cubic-bezier(0, 0, 0.2, 1);\n  opacity: 1;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:checked ~ .mdc-checkbox__background > .mdc-checkbox__mixedmark {\n  transform: scaleX(1) rotate(-45deg);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background > .mdc-checkbox__checkmark {\n  transform: rotate(45deg);\n  opacity: 0;\n  transition: opacity 90ms cubic-bezier(0.4, 0, 0.6, 1), transform 90ms cubic-bezier(0.4, 0, 0.6, 1);\n}\n.mat-mdc-list-option .mdc-checkbox__native-control:indeterminate ~ .mdc-checkbox__background > .mdc-checkbox__mixedmark {\n  transform: scaleX(1) rotate(0deg);\n  opacity: 1;\n}\n@keyframes mdc-checkbox-unchecked-checked-checkmark-path {\n  0%, 50% {\n    stroke-dashoffset: 29.7833385;\n  }\n  50% {\n    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);\n  }\n  100% {\n    stroke-dashoffset: 0;\n  }\n}\n@keyframes mdc-checkbox-unchecked-indeterminate-mixedmark {\n  0%, 68.2% {\n    transform: scaleX(0);\n  }\n  68.2% {\n    animation-timing-function: cubic-bezier(0, 0, 0, 1);\n  }\n  100% {\n    transform: scaleX(1);\n  }\n}\n@keyframes mdc-checkbox-checked-unchecked-checkmark-path {\n  from {\n    animation-timing-function: cubic-bezier(0.4, 0, 1, 1);\n    opacity: 1;\n    stroke-dashoffset: 0;\n  }\n  to {\n    opacity: 0;\n    stroke-dashoffset: -29.7833385;\n  }\n}\n@keyframes mdc-checkbox-checked-indeterminate-checkmark {\n  from {\n    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);\n    transform: rotate(0deg);\n    opacity: 1;\n  }\n  to {\n    transform: rotate(45deg);\n    opacity: 0;\n  }\n}\n@keyframes mdc-checkbox-indeterminate-checked-checkmark {\n  from {\n    animation-timing-function: cubic-bezier(0.14, 0, 0, 1);\n    transform: rotate(45deg);\n    opacity: 0;\n  }\n  to {\n    transform: rotate(360deg);\n    opacity: 1;\n  }\n}\n@keyframes mdc-checkbox-checked-indeterminate-mixedmark {\n  from {\n    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);\n    transform: rotate(-45deg);\n    opacity: 0;\n  }\n  to {\n    transform: rotate(0deg);\n    opacity: 1;\n  }\n}\n@keyframes mdc-checkbox-indeterminate-checked-mixedmark {\n  from {\n    animation-timing-function: cubic-bezier(0.14, 0, 0, 1);\n    transform: rotate(0deg);\n    opacity: 1;\n  }\n  to {\n    transform: rotate(315deg);\n    opacity: 0;\n  }\n}\n@keyframes mdc-checkbox-indeterminate-unchecked-mixedmark {\n  0% {\n    animation-timing-function: linear;\n    transform: scaleX(1);\n    opacity: 1;\n  }\n  32.8%, 100% {\n    transform: scaleX(0);\n    opacity: 0;\n  }\n}\n.mat-mdc-list-option .mdc-radio {\n  display: inline-block;\n  position: relative;\n  flex: 0 0 auto;\n  box-sizing: content-box;\n  width: 20px;\n  height: 20px;\n  cursor: pointer;\n  will-change: opacity, transform, border-color, color;\n  padding: calc((var(--mat-radio-state-layer-size, 40px) - 20px) / 2);\n}\n.mat-mdc-list-option .mdc-radio__background {\n  display: inline-block;\n  position: relative;\n  box-sizing: border-box;\n  width: 20px;\n  height: 20px;\n}\n.mat-mdc-list-option .mdc-radio__background::before {\n  position: absolute;\n  transform: scale(0, 0);\n  border-radius: 50%;\n  opacity: 0;\n  pointer-events: none;\n  content: "";\n  transition: opacity 90ms cubic-bezier(0.4, 0, 0.6, 1), transform 90ms cubic-bezier(0.4, 0, 0.6, 1);\n  width: var(--mat-radio-state-layer-size, 40px);\n  height: var(--mat-radio-state-layer-size, 40px);\n  top: calc(-1 * (var(--mat-radio-state-layer-size, 40px) - 20px) / 2);\n  left: calc(-1 * (var(--mat-radio-state-layer-size, 40px) - 20px) / 2);\n}\n.mat-mdc-list-option .mdc-radio__outer-circle {\n  position: absolute;\n  top: 0;\n  left: 0;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  border-width: 2px;\n  border-style: solid;\n  border-radius: 50%;\n  transition: border-color 90ms cubic-bezier(0.4, 0, 0.6, 1);\n}\n.mat-mdc-list-option .mdc-radio__inner-circle {\n  position: absolute;\n  top: 0;\n  left: 0;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  transform: scale(0);\n  border-radius: 50%;\n  transition: transform 90ms cubic-bezier(0.4, 0, 0.6, 1), background-color 90ms cubic-bezier(0.4, 0, 0.6, 1);\n}\n@media (forced-colors: active) {\n  .mat-mdc-list-option .mdc-radio__inner-circle {\n    background-color: CanvasText !important;\n  }\n}\n.mat-mdc-list-option .mdc-radio__native-control {\n  position: absolute;\n  margin: 0;\n  padding: 0;\n  opacity: 0;\n  top: 0;\n  right: 0;\n  left: 0;\n  cursor: inherit;\n  z-index: 1;\n  width: var(--mat-radio-state-layer-size, 40px);\n  height: var(--mat-radio-state-layer-size, 40px);\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background, .mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background {\n  transition: opacity 90ms cubic-bezier(0, 0, 0.2, 1), transform 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background > .mdc-radio__outer-circle, .mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__outer-circle {\n  transition: border-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background > .mdc-radio__inner-circle, .mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__inner-circle {\n  transition: transform 90ms cubic-bezier(0, 0, 0.2, 1), background-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled:not(:checked) + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-disabled-unselected-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-radio-disabled-unselected-icon-opacity, 0.38);\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background {\n  cursor: default;\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-disabled-selected-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-radio-disabled-selected-icon-opacity, 0.38);\n}\n.mat-mdc-list-option .mdc-radio__native-control:disabled + .mdc-radio__background > .mdc-radio__inner-circle {\n  background-color: var(--mat-radio-disabled-selected-icon-color, var(--mat-sys-on-surface, currentColor));\n  opacity: var(--mat-radio-disabled-selected-icon-opacity, 0.38);\n}\n.mat-mdc-list-option .mdc-radio__native-control:enabled:not(:checked) + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-unselected-icon-color, var(--mat-sys-on-surface-variant));\n}\n.mat-mdc-list-option .mdc-radio__native-control:enabled:checked + .mdc-radio__background > .mdc-radio__outer-circle {\n  border-color: var(--mat-radio-selected-icon-color, var(--mat-sys-primary));\n}\n.mat-mdc-list-option .mdc-radio__native-control:enabled:checked + .mdc-radio__background > .mdc-radio__inner-circle {\n  background-color: var(--mat-radio-selected-icon-color, var(--mat-sys-primary, currentColor));\n}\n.mat-mdc-list-option .mdc-radio__native-control:checked + .mdc-radio__background > .mdc-radio__inner-circle {\n  transform: scale(0.5);\n  transition: transform 90ms cubic-bezier(0, 0, 0.2, 1), background-color 90ms cubic-bezier(0, 0, 0.2, 1);\n}\n.mat-mdc-list-option._mat-animation-noopable .mdc-radio__background::before,\n.mat-mdc-list-option._mat-animation-noopable .mdc-radio__outer-circle,\n.mat-mdc-list-option._mat-animation-noopable .mdc-radio__inner-circle {\n  transition: none !important;\n}\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mat-mdc-checkbox-touch-target,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__native-control,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__ripple,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mat-mdc-checkbox-ripple::before,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__start > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__mixedmark, .mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mat-mdc-checkbox-touch-target,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__native-control,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__ripple,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mat-mdc-checkbox-ripple::before,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__checkmark > .mdc-checkbox__checkmark-path,\n.mat-mdc-list-option._mat-animation-noopable > .mdc-list-item__end > .mdc-checkbox > .mdc-checkbox__background > .mdc-checkbox__mixedmark {\n  transition: none !important;\n  animation: none !important;\n}\n.mat-mdc-list-option .mdc-checkbox__native-control, .mat-mdc-list-option .mdc-radio__native-control {\n  display: none;\n}\n\n@media (forced-colors: active) {\n  .mat-mdc-list-option.mdc-list-item--selected::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  .mat-mdc-list-option.mdc-list-item--selected [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n']
    }]
  }], null, {
    _lines: [{
      type: ContentChildren,
      args: [MatListItemLine, {
        descendants: true
      }]
    }],
    _titles: [{
      type: ContentChildren,
      args: [MatListItemTitle, {
        descendants: true
      }]
    }],
    _unscopedContent: [{
      type: ViewChild,
      args: ["unscopedContent"]
    }],
    selectedChange: [{
      type: Output
    }],
    togglePosition: [{
      type: Input
    }],
    checkboxPosition: [{
      type: Input
    }],
    color: [{
      type: Input
    }],
    value: [{
      type: Input
    }],
    selected: [{
      type: Input
    }]
  });
})();
var MatListSubheaderCssMatStyler = class _MatListSubheaderCssMatStyler {
  static ɵfac = function MatListSubheaderCssMatStyler_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListSubheaderCssMatStyler)();
  };
  static ɵdir = ɵɵdefineDirective({
    type: _MatListSubheaderCssMatStyler,
    selectors: [["", "mat-subheader", ""], ["", "matSubheader", ""]],
    hostAttrs: [1, "mat-mdc-subheader", "mdc-list-group__subheader"]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListSubheaderCssMatStyler, [{
    type: Directive,
    args: [{
      selector: "[mat-subheader], [matSubheader]",
      host: {
        "class": "mat-mdc-subheader mdc-list-group__subheader"
      }
    }]
  }], null, null);
})();
var MAT_NAV_LIST = new InjectionToken("MatNavList");
var MatNavList = class _MatNavList extends MatListBase {
  _isNonInteractive = false;
  static ɵfac = /* @__PURE__ */ (() => {
    let ɵMatNavList_BaseFactory;
    return function MatNavList_Factory(__ngFactoryType__) {
      return (ɵMatNavList_BaseFactory || (ɵMatNavList_BaseFactory = ɵɵgetInheritedFactory(_MatNavList)))(__ngFactoryType__ || _MatNavList);
    };
  })();
  static ɵcmp = ɵɵdefineComponent({
    type: _MatNavList,
    selectors: [["mat-nav-list"]],
    hostAttrs: ["role", "navigation", 1, "mat-mdc-nav-list", "mat-mdc-list-base", "mdc-list"],
    exportAs: ["matNavList"],
    features: [ɵɵProvidersFeature([{
      provide: MatListBase,
      useExisting: _MatNavList
    }]), ɵɵInheritDefinitionFeature],
    ngContentSelectors: _c0,
    decls: 1,
    vars: 0,
    template: function MatNavList_Template(rf, ctx) {
      if (rf & 1) {
        ɵɵprojectionDef();
        ɵɵprojection(0);
      }
    },
    styles: [_c1],
    encapsulation: 2,
    changeDetection: 0
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatNavList, [{
    type: Component,
    args: [{
      selector: "mat-nav-list",
      exportAs: "matNavList",
      template: "<ng-content></ng-content>",
      host: {
        "class": "mat-mdc-nav-list mat-mdc-list-base mdc-list",
        "role": "navigation"
      },
      encapsulation: ViewEncapsulation.None,
      changeDetection: ChangeDetectionStrategy.OnPush,
      providers: [{
        provide: MatListBase,
        useExisting: MatNavList
      }],
      styles: ['.mdc-list {\n  margin: 0;\n  padding: 8px 0;\n  list-style-type: none;\n}\n.mdc-list:focus {\n  outline: none;\n}\n\n.mdc-list-item {\n  display: flex;\n  position: relative;\n  justify-content: flex-start;\n  overflow: hidden;\n  padding: 0;\n  align-items: stretch;\n  cursor: pointer;\n  padding-left: 16px;\n  padding-right: 16px;\n  background-color: var(--mat-list-list-item-container-color, transparent);\n  border-radius: var(--mat-list-list-item-container-shape, var(--mat-sys-corner-none));\n}\n.mdc-list-item.mdc-list-item--selected {\n  background-color: var(--mat-list-list-item-selected-container-color);\n}\n.mdc-list-item:focus {\n  outline: 0;\n}\n.mdc-list-item.mdc-list-item--disabled {\n  cursor: auto;\n}\n.mdc-list-item.mdc-list-item--with-one-line {\n  height: var(--mat-list-list-item-one-line-container-height, 48px);\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__start {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-two-lines {\n  height: var(--mat-list-list-item-two-line-container-height, 64px);\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-three-lines {\n  height: var(--mat-list-list-item-three-line-container-height, 88px);\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--selected::before, .mdc-list-item.mdc-list-item--selected:focus::before, .mdc-list-item:not(.mdc-list-item--selected):focus::before {\n  position: absolute;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  content: "";\n  pointer-events: none;\n}\n\na.mdc-list-item {\n  color: inherit;\n  text-decoration: none;\n}\n\n.mdc-list-item__start {\n  fill: currentColor;\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-leading-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-leading-icon-size, 24px);\n  height: var(--mat-list-list-item-leading-icon-size, 24px);\n  margin-left: 16px;\n  margin-right: 32px;\n}\n[dir=rtl] .mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-left: 32px;\n  margin-right: 16px;\n}\n.mdc-list-item--with-leading-icon:hover .mdc-list-item__start {\n  color: var(--mat-list-list-item-hover-leading-icon-color);\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  width: var(--mat-list-list-item-leading-avatar-size, 40px);\n  height: var(--mat-list-list-item-leading-avatar-size, 40px);\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start, [dir=rtl] .mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n\n.mdc-list-item__end {\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  font-family: var(--mat-list-list-item-trailing-supporting-text-font, var(--mat-sys-label-small-font));\n  line-height: var(--mat-list-list-item-trailing-supporting-text-line-height, var(--mat-sys-label-small-line-height));\n  font-size: var(--mat-list-list-item-trailing-supporting-text-size, var(--mat-sys-label-small-size));\n  font-weight: var(--mat-list-list-item-trailing-supporting-text-weight, var(--mat-sys-label-small-weight));\n  letter-spacing: var(--mat-list-list-item-trailing-supporting-text-tracking, var(--mat-sys-label-small-tracking));\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-trailing-icon-size, 24px);\n  height: var(--mat-list-list-item-trailing-icon-size, 24px);\n}\n.mdc-list-item--with-trailing-icon:hover .mdc-list-item__end {\n  color: var(--mat-list-list-item-hover-trailing-icon-color);\n}\n.mdc-list-item.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-supporting-text-color, var(--mat-sys-on-surface-variant));\n}\n.mdc-list-item--selected.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-selected-trailing-icon-color, var(--mat-sys-primary));\n}\n\n.mdc-list-item__content {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  align-self: center;\n  flex: 1;\n  pointer-events: none;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__content, .mdc-list-item--with-three-lines .mdc-list-item__content {\n  align-self: stretch;\n}\n\n.mdc-list-item__primary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  color: var(--mat-list-list-item-label-text-color, var(--mat-sys-on-surface));\n  font-family: var(--mat-list-list-item-label-text-font, var(--mat-sys-body-large-font));\n  line-height: var(--mat-list-list-item-label-text-line-height, var(--mat-sys-body-large-line-height));\n  font-size: var(--mat-list-list-item-label-text-size, var(--mat-sys-body-large-size));\n  font-weight: var(--mat-list-list-item-label-text-weight, var(--mat-sys-body-large-weight));\n  letter-spacing: var(--mat-list-list-item-label-text-tracking, var(--mat-sys-body-large-tracking));\n}\n.mdc-list-item:hover .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-hover-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item:focus .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-focus-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text, .mdc-list-item--with-three-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n\n.mdc-list-item__secondary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  display: block;\n  margin-top: 0;\n  color: var(--mat-list-list-item-supporting-text-color, var(--mat-sys-on-surface-variant));\n  font-family: var(--mat-list-list-item-supporting-text-font, var(--mat-sys-body-medium-font));\n  line-height: var(--mat-list-list-item-supporting-text-line-height, var(--mat-sys-body-medium-line-height));\n  font-size: var(--mat-list-list-item-supporting-text-size, var(--mat-sys-body-medium-size));\n  font-weight: var(--mat-list-list-item-supporting-text-weight, var(--mat-sys-body-medium-weight));\n  letter-spacing: var(--mat-list-list-item-supporting-text-tracking, var(--mat-sys-body-medium-tracking));\n}\n.mdc-list-item__secondary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-three-lines .mdc-list-item__secondary-text {\n  white-space: normal;\n  line-height: 20px;\n}\n.mdc-list-item--with-overline .mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: auto;\n}\n\n.mdc-list-item--with-leading-radio.mdc-list-item,\n.mdc-list-item--with-leading-checkbox.mdc-list-item,\n.mdc-list-item--with-leading-icon.mdc-list-item,\n.mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-checkbox.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-icon.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-trailing-icon.mdc-list-item, [dir=rtl] .mdc-list-item--with-trailing-icon.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n}\n\n.mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  -webkit-user-select: none;\n  user-select: none;\n  margin-left: 28px;\n  margin-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 28px;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end {\n  display: block;\n  line-height: normal;\n  align-self: flex-start;\n  margin-top: 0;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end::before, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-leading-radio .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio .mdc-list-item__start,\n[dir=rtl] .mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-item--with-trailing-radio.mdc-list-item,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-left: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, [dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-radio .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio .mdc-list-item__end,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-three-lines .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-group__subheader {\n  margin: 0.75rem 16px;\n}\n\n.mdc-list-item--disabled .mdc-list-item__start,\n.mdc-list-item--disabled .mdc-list-item__content,\n.mdc-list-item--disabled .mdc-list-item__end {\n  opacity: 1;\n}\n.mdc-list-item--disabled .mdc-list-item__primary-text,\n.mdc-list-item--disabled .mdc-list-item__secondary-text {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n.mdc-list-item--disabled.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-disabled-leading-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-leading-icon-opacity, 0.38);\n}\n.mdc-list-item--disabled.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-disabled-trailing-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-trailing-icon-opacity, 0.38);\n}\n\n.mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing, [dir=rtl] .mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing {\n  padding-left: 0;\n  padding-right: 0;\n}\n\n.mdc-list-item.mdc-list-item--disabled .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-disabled-label-text-color, var(--mat-sys-on-surface));\n}\n\n.mdc-list-item:hover::before {\n  background-color: var(--mat-list-list-item-hover-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-hover-state-layer-opacity, var(--mat-sys-hover-state-layer-opacity));\n}\n\n.mdc-list-item.mdc-list-item--disabled::before {\n  background-color: var(--mat-list-list-item-disabled-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item:focus::before {\n  background-color: var(--mat-list-list-item-focus-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-focus-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item--disabled .mdc-radio,\n.mdc-list-item--disabled .mdc-checkbox {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n\n.mdc-list-item--with-leading-avatar .mat-mdc-list-item-avatar {\n  border-radius: var(--mat-list-list-item-leading-avatar-shape, var(--mat-sys-corner-full));\n  background-color: var(--mat-list-list-item-leading-avatar-color, var(--mat-sys-primary-container));\n}\n\n.mat-mdc-list-item-icon {\n  font-size: var(--mat-list-list-item-leading-icon-size, 24px);\n}\n\n@media (forced-colors: active) {\n  a.mdc-list-item--activated::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  a.mdc-list-item--activated [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n\n.mat-mdc-list-base {\n  display: block;\n}\n.mat-mdc-list-base .mdc-list-item__start,\n.mat-mdc-list-base .mdc-list-item__end,\n.mat-mdc-list-base .mdc-list-item__content {\n  pointer-events: auto;\n}\n\n.mat-mdc-list-item,\n.mat-mdc-list-option {\n  width: 100%;\n  box-sizing: border-box;\n  -webkit-tap-highlight-color: transparent;\n}\n.mat-mdc-list-item:not(.mat-mdc-list-item-interactive),\n.mat-mdc-list-option:not(.mat-mdc-list-item-interactive) {\n  cursor: default;\n}\n.mat-mdc-list-item .mat-divider-inset,\n.mat-mdc-list-option .mat-divider-inset {\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n.mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n.mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-left: 72px;\n}\n[dir=rtl] .mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n[dir=rtl] .mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-right: 72px;\n}\n\n.mat-mdc-list-item-interactive::before {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  content: "";\n  opacity: 0;\n  pointer-events: none;\n  border-radius: inherit;\n}\n\n.mat-mdc-list-item > .mat-focus-indicator {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  pointer-events: none;\n}\n.mat-mdc-list-item:focus-visible > .mat-focus-indicator::before {\n  content: "";\n}\n\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-line.mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: normal;\n}\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-unscoped-content.mdc-list-item__secondary-text {\n  display: -webkit-box;\n  -webkit-box-orient: vertical;\n  -webkit-line-clamp: 2;\n}\n\nmat-action-list button {\n  background: none;\n  color: inherit;\n  border: none;\n  font: inherit;\n  outline: inherit;\n  -webkit-tap-highlight-color: transparent;\n  text-align: start;\n}\nmat-action-list button::-moz-focus-inner {\n  border: 0;\n}\n\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-inline-start: var(--mat-list-list-item-leading-icon-start-space, 16px);\n  margin-inline-end: var(--mat-list-list-item-leading-icon-end-space, 16px);\n}\n\n.mat-mdc-nav-list .mat-mdc-list-item {\n  border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n  --mat-focus-indicator-border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n}\n.mat-mdc-nav-list .mat-mdc-list-item.mdc-list-item--activated {\n  background-color: var(--mat-list-active-indicator-color, var(--mat-sys-secondary-container));\n}\n']
    }]
  }], null, null);
})();
var MAT_SELECTION_LIST_VALUE_ACCESSOR = {
  provide: NG_VALUE_ACCESSOR,
  useExisting: forwardRef(() => MatSelectionList),
  multi: true
};
var MatSelectionListChange = class {
  source;
  options;
  constructor(source, options) {
    this.source = source;
    this.options = options;
  }
};
var MatSelectionList = class _MatSelectionList extends MatListBase {
  _element = inject(ElementRef);
  _ngZone = inject(NgZone);
  _renderer = inject(Renderer2);
  _initialized = false;
  _keyManager;
  _listenerCleanups;
  _destroyed = new Subject();
  _isDestroyed = false;
  _onChange = (_) => {
  };
  _items;
  selectionChange = new EventEmitter();
  color = "accent";
  compareWith = (a1, a2) => a1 === a2;
  get multiple() {
    return this._multiple;
  }
  set multiple(value) {
    const newValue = coerceBooleanProperty(value);
    if (newValue !== this._multiple) {
      if ((typeof ngDevMode === "undefined" || ngDevMode) && this._initialized) {
        throw new Error("Cannot change `multiple` mode of mat-selection-list after initialization.");
      }
      this._multiple = newValue;
      this.selectedOptions = new SelectionModel(this._multiple, this.selectedOptions.selected);
    }
  }
  _multiple = true;
  get hideSingleSelectionIndicator() {
    return this._hideSingleSelectionIndicator;
  }
  set hideSingleSelectionIndicator(value) {
    this._hideSingleSelectionIndicator = coerceBooleanProperty(value);
  }
  _hideSingleSelectionIndicator = this._defaultOptions?.hideSingleSelectionIndicator ?? false;
  selectedOptions = new SelectionModel(this._multiple);
  _value = null;
  _onTouched = () => {
  };
  _changeDetectorRef = inject(ChangeDetectorRef);
  constructor() {
    super();
    this._isNonInteractive = false;
  }
  ngAfterViewInit() {
    this._initialized = true;
    this._setupRovingTabindex();
    this._ngZone.runOutsideAngular(() => {
      this._listenerCleanups = [this._renderer.listen(this._element.nativeElement, "focusin", this._handleFocusin), this._renderer.listen(this._element.nativeElement, "focusout", this._handleFocusout)];
    });
    if (this._value) {
      this._setOptionsFromValues(this._value);
    }
    this._watchForSelectionChange();
  }
  ngOnChanges(changes) {
    const disabledChanges = changes["disabled"];
    const disableRippleChanges = changes["disableRipple"];
    const hideSingleSelectionIndicatorChanges = changes["hideSingleSelectionIndicator"];
    if (disableRippleChanges && !disableRippleChanges.firstChange || disabledChanges && !disabledChanges.firstChange || hideSingleSelectionIndicatorChanges && !hideSingleSelectionIndicatorChanges.firstChange) {
      this._markOptionsForCheck();
    }
  }
  ngOnDestroy() {
    this._keyManager?.destroy();
    this._listenerCleanups?.forEach((current) => current());
    this._destroyed.next();
    this._destroyed.complete();
    this._isDestroyed = true;
  }
  focus(options) {
    this._element.nativeElement.focus(options);
  }
  selectAll() {
    return this._setAllOptionsSelected(true);
  }
  deselectAll() {
    return this._setAllOptionsSelected(false);
  }
  _reportValueChange() {
    if (this.options && !this._isDestroyed) {
      const value = this._getSelectedOptionValues();
      this._onChange(value);
      this._value = value;
    }
  }
  _emitChangeEvent(options) {
    this.selectionChange.emit(new MatSelectionListChange(this, options));
  }
  writeValue(values) {
    this._value = values;
    if (this.options) {
      this._setOptionsFromValues(values || []);
    }
  }
  setDisabledState(isDisabled) {
    this.disabled = isDisabled;
    this._changeDetectorRef.markForCheck();
    this._markOptionsForCheck();
  }
  get disabled() {
    return this._selectionListDisabled();
  }
  set disabled(value) {
    this._selectionListDisabled.set(coerceBooleanProperty(value));
    if (this._selectionListDisabled()) {
      this._keyManager?.setActiveItem(-1);
    }
  }
  _selectionListDisabled = signal(false, ...ngDevMode ? [{
    debugName: "_selectionListDisabled"
  }] : []);
  registerOnChange(fn) {
    this._onChange = fn;
  }
  registerOnTouched(fn) {
    this._onTouched = fn;
  }
  _watchForSelectionChange() {
    this.selectedOptions.changed.pipe(takeUntil(this._destroyed)).subscribe((event) => {
      for (let item of event.added) {
        item.selected = true;
      }
      for (let item of event.removed) {
        item.selected = false;
      }
      if (!this._containsFocus()) {
        this._resetActiveOption();
      }
    });
  }
  _setOptionsFromValues(values) {
    this.options.forEach((option) => option._setSelected(false));
    values.forEach((value) => {
      const correspondingOption = this.options.find((option) => {
        return option.selected ? false : this.compareWith(option.value, value);
      });
      if (correspondingOption) {
        correspondingOption._setSelected(true);
      }
    });
  }
  _getSelectedOptionValues() {
    return this.options.filter((option) => option.selected).map((option) => option.value);
  }
  _markOptionsForCheck() {
    if (this.options) {
      this.options.forEach((option) => option._markForCheck());
    }
  }
  _setAllOptionsSelected(isSelected, skipDisabled) {
    const changedOptions = [];
    this.options.forEach((option) => {
      if ((!skipDisabled || !option.disabled) && option._setSelected(isSelected)) {
        changedOptions.push(option);
      }
    });
    if (changedOptions.length) {
      this._reportValueChange();
    }
    return changedOptions;
  }
  get options() {
    return this._items;
  }
  _handleKeydown(event) {
    const activeItem = this._keyManager.activeItem;
    if ((event.keyCode === ENTER || event.keyCode === SPACE) && !this._keyManager.isTyping() && activeItem && !activeItem.disabled) {
      event.preventDefault();
      activeItem._toggleOnInteraction();
    } else if (event.keyCode === A && this.multiple && !this._keyManager.isTyping() && hasModifierKey(event, "ctrlKey", "metaKey")) {
      const shouldSelect = this.options.some((option) => !option.disabled && !option.selected);
      event.preventDefault();
      this._emitChangeEvent(this._setAllOptionsSelected(shouldSelect, true));
    } else {
      this._keyManager.onKeydown(event);
    }
  }
  _handleFocusout = () => {
    setTimeout(() => {
      if (!this._containsFocus()) {
        this._resetActiveOption();
      }
    });
  };
  _handleFocusin = (event) => {
    if (this.disabled) {
      return;
    }
    const activeIndex = this._items.toArray().findIndex((item) => item._elementRef.nativeElement.contains(event.target));
    if (activeIndex > -1) {
      this._setActiveOption(activeIndex);
    } else {
      this._resetActiveOption();
    }
  };
  _setupRovingTabindex() {
    this._keyManager = new FocusKeyManager(this._items).withHomeAndEnd().withTypeAhead().withWrap().skipPredicate(() => this.disabled);
    this._resetActiveOption();
    this._keyManager.change.subscribe((activeItemIndex) => this._setActiveOption(activeItemIndex));
    this._items.changes.pipe(takeUntil(this._destroyed)).subscribe(() => {
      const activeItem = this._keyManager.activeItem;
      if (!activeItem || this._items.toArray().indexOf(activeItem) === -1) {
        this._resetActiveOption();
      }
    });
  }
  _setActiveOption(index) {
    this._items.forEach((item, itemIndex) => item._setTabindex(itemIndex === index ? 0 : -1));
    this._keyManager.updateActiveItem(index);
  }
  _resetActiveOption() {
    if (this.disabled) {
      this._setActiveOption(-1);
      return;
    }
    const activeItem = this._items.find((item) => item.selected && !item.disabled) || this._items.first;
    this._setActiveOption(activeItem ? this._items.toArray().indexOf(activeItem) : -1);
  }
  _containsFocus() {
    const activeElement = _getFocusedElementPierceShadowDom();
    return activeElement && this._element.nativeElement.contains(activeElement);
  }
  static ɵfac = function MatSelectionList_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatSelectionList)();
  };
  static ɵcmp = ɵɵdefineComponent({
    type: _MatSelectionList,
    selectors: [["mat-selection-list"]],
    contentQueries: function MatSelectionList_ContentQueries(rf, ctx, dirIndex) {
      if (rf & 1) {
        ɵɵcontentQuery(dirIndex, MatListOption, 5);
      }
      if (rf & 2) {
        let _t;
        ɵɵqueryRefresh(_t = ɵɵloadQuery()) && (ctx._items = _t);
      }
    },
    hostAttrs: ["role", "listbox", 1, "mat-mdc-selection-list", "mat-mdc-list-base", "mdc-list"],
    hostVars: 1,
    hostBindings: function MatSelectionList_HostBindings(rf, ctx) {
      if (rf & 1) {
        ɵɵlistener("keydown", function MatSelectionList_keydown_HostBindingHandler($event) {
          return ctx._handleKeydown($event);
        });
      }
      if (rf & 2) {
        ɵɵattribute("aria-multiselectable", ctx.multiple);
      }
    },
    inputs: {
      color: "color",
      compareWith: "compareWith",
      multiple: "multiple",
      hideSingleSelectionIndicator: "hideSingleSelectionIndicator",
      disabled: "disabled"
    },
    outputs: {
      selectionChange: "selectionChange"
    },
    exportAs: ["matSelectionList"],
    features: [ɵɵProvidersFeature([MAT_SELECTION_LIST_VALUE_ACCESSOR, {
      provide: MatListBase,
      useExisting: _MatSelectionList
    }, {
      provide: SELECTION_LIST,
      useExisting: _MatSelectionList
    }]), ɵɵInheritDefinitionFeature, ɵɵNgOnChangesFeature],
    ngContentSelectors: _c0,
    decls: 1,
    vars: 0,
    template: function MatSelectionList_Template(rf, ctx) {
      if (rf & 1) {
        ɵɵprojectionDef();
        ɵɵprojection(0);
      }
    },
    styles: [_c1],
    encapsulation: 2,
    changeDetection: 0
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatSelectionList, [{
    type: Component,
    args: [{
      selector: "mat-selection-list",
      exportAs: "matSelectionList",
      host: {
        "class": "mat-mdc-selection-list mat-mdc-list-base mdc-list",
        "role": "listbox",
        "[attr.aria-multiselectable]": "multiple",
        "(keydown)": "_handleKeydown($event)"
      },
      template: "<ng-content></ng-content>",
      encapsulation: ViewEncapsulation.None,
      providers: [MAT_SELECTION_LIST_VALUE_ACCESSOR, {
        provide: MatListBase,
        useExisting: MatSelectionList
      }, {
        provide: SELECTION_LIST,
        useExisting: MatSelectionList
      }],
      changeDetection: ChangeDetectionStrategy.OnPush,
      styles: ['.mdc-list {\n  margin: 0;\n  padding: 8px 0;\n  list-style-type: none;\n}\n.mdc-list:focus {\n  outline: none;\n}\n\n.mdc-list-item {\n  display: flex;\n  position: relative;\n  justify-content: flex-start;\n  overflow: hidden;\n  padding: 0;\n  align-items: stretch;\n  cursor: pointer;\n  padding-left: 16px;\n  padding-right: 16px;\n  background-color: var(--mat-list-list-item-container-color, transparent);\n  border-radius: var(--mat-list-list-item-container-shape, var(--mat-sys-corner-none));\n}\n.mdc-list-item.mdc-list-item--selected {\n  background-color: var(--mat-list-list-item-selected-container-color);\n}\n.mdc-list-item:focus {\n  outline: 0;\n}\n.mdc-list-item.mdc-list-item--disabled {\n  cursor: auto;\n}\n.mdc-list-item.mdc-list-item--with-one-line {\n  height: var(--mat-list-list-item-one-line-container-height, 48px);\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__start {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-one-line .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-two-lines {\n  height: var(--mat-list-list-item-two-line-container-height, 64px);\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-two-lines .mdc-list-item__end {\n  align-self: center;\n  margin-top: 0;\n}\n.mdc-list-item.mdc-list-item--with-three-lines {\n  height: var(--mat-list-list-item-three-line-container-height, 88px);\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 16px;\n}\n.mdc-list-item.mdc-list-item--selected::before, .mdc-list-item.mdc-list-item--selected:focus::before, .mdc-list-item:not(.mdc-list-item--selected):focus::before {\n  position: absolute;\n  box-sizing: border-box;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  content: "";\n  pointer-events: none;\n}\n\na.mdc-list-item {\n  color: inherit;\n  text-decoration: none;\n}\n\n.mdc-list-item__start {\n  fill: currentColor;\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-leading-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-leading-icon-size, 24px);\n  height: var(--mat-list-list-item-leading-icon-size, 24px);\n  margin-left: 16px;\n  margin-right: 32px;\n}\n[dir=rtl] .mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-left: 32px;\n  margin-right: 16px;\n}\n.mdc-list-item--with-leading-icon:hover .mdc-list-item__start {\n  color: var(--mat-list-list-item-hover-leading-icon-color);\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  width: var(--mat-list-list-item-leading-avatar-size, 40px);\n  height: var(--mat-list-list-item-leading-avatar-size, 40px);\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n.mdc-list-item--with-leading-avatar .mdc-list-item__start, [dir=rtl] .mdc-list-item--with-leading-avatar .mdc-list-item__start {\n  margin-left: 16px;\n  margin-right: 16px;\n  border-radius: 50%;\n}\n\n.mdc-list-item__end {\n  flex-shrink: 0;\n  pointer-events: none;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  font-family: var(--mat-list-list-item-trailing-supporting-text-font, var(--mat-sys-label-small-font));\n  line-height: var(--mat-list-list-item-trailing-supporting-text-line-height, var(--mat-sys-label-small-line-height));\n  font-size: var(--mat-list-list-item-trailing-supporting-text-size, var(--mat-sys-label-small-size));\n  font-weight: var(--mat-list-list-item-trailing-supporting-text-weight, var(--mat-sys-label-small-weight));\n  letter-spacing: var(--mat-list-list-item-trailing-supporting-text-tracking, var(--mat-sys-label-small-tracking));\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-icon-color, var(--mat-sys-on-surface-variant));\n  width: var(--mat-list-list-item-trailing-icon-size, 24px);\n  height: var(--mat-list-list-item-trailing-icon-size, 24px);\n}\n.mdc-list-item--with-trailing-icon:hover .mdc-list-item__end {\n  color: var(--mat-list-list-item-hover-trailing-icon-color);\n}\n.mdc-list-item.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  color: var(--mat-list-list-item-trailing-supporting-text-color, var(--mat-sys-on-surface-variant));\n}\n.mdc-list-item--selected.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-selected-trailing-icon-color, var(--mat-sys-primary));\n}\n\n.mdc-list-item__content {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  align-self: center;\n  flex: 1;\n  pointer-events: none;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__content, .mdc-list-item--with-three-lines .mdc-list-item__content {\n  align-self: stretch;\n}\n\n.mdc-list-item__primary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  color: var(--mat-list-list-item-label-text-color, var(--mat-sys-on-surface));\n  font-family: var(--mat-list-list-item-label-text-font, var(--mat-sys-body-large-font));\n  line-height: var(--mat-list-list-item-label-text-line-height, var(--mat-sys-body-large-line-height));\n  font-size: var(--mat-list-list-item-label-text-size, var(--mat-sys-body-large-size));\n  font-weight: var(--mat-list-list-item-label-text-weight, var(--mat-sys-body-large-weight));\n  letter-spacing: var(--mat-list-list-item-label-text-tracking, var(--mat-sys-body-large-tracking));\n}\n.mdc-list-item:hover .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-hover-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item:focus .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-focus-label-text-color, var(--mat-sys-on-surface));\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text, .mdc-list-item--with-three-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after, .mdc-list-item--with-three-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n\n.mdc-list-item__secondary-text {\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  overflow: hidden;\n  display: block;\n  margin-top: 0;\n  color: var(--mat-list-list-item-supporting-text-color, var(--mat-sys-on-surface-variant));\n  font-family: var(--mat-list-list-item-supporting-text-font, var(--mat-sys-body-medium-font));\n  line-height: var(--mat-list-list-item-supporting-text-line-height, var(--mat-sys-body-medium-line-height));\n  font-size: var(--mat-list-list-item-supporting-text-size, var(--mat-sys-body-medium-size));\n  font-weight: var(--mat-list-list-item-supporting-text-weight, var(--mat-sys-body-medium-weight));\n  letter-spacing: var(--mat-list-list-item-supporting-text-tracking, var(--mat-sys-body-medium-tracking));\n}\n.mdc-list-item__secondary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-three-lines .mdc-list-item__secondary-text {\n  white-space: normal;\n  line-height: 20px;\n}\n.mdc-list-item--with-overline .mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: auto;\n}\n\n.mdc-list-item--with-leading-radio.mdc-list-item,\n.mdc-list-item--with-leading-checkbox.mdc-list-item,\n.mdc-list-item--with-leading-icon.mdc-list-item,\n.mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-checkbox.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-icon.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-leading-avatar.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n  margin-bottom: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines .mdc-list-item__primary-text::after {\n  display: inline-block;\n  width: 0;\n  height: 20px;\n  content: "";\n  vertical-align: -20px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  display: block;\n  margin-top: 0;\n  line-height: normal;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-icon.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before,\n.mdc-list-item--with-leading-avatar.mdc-list-item--with-two-lines.mdc-list-item--with-trailing-meta .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 32px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-trailing-icon.mdc-list-item, [dir=rtl] .mdc-list-item--with-trailing-icon.mdc-list-item {\n  padding-left: 0;\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 16px;\n}\n\n.mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  -webkit-user-select: none;\n  user-select: none;\n  margin-left: 28px;\n  margin-right: 16px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-meta .mdc-list-item__end {\n  margin-left: 16px;\n  margin-right: 28px;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end {\n  display: block;\n  line-height: normal;\n  align-self: flex-start;\n  margin-top: 0;\n}\n.mdc-list-item--with-trailing-meta.mdc-list-item--with-three-lines .mdc-list-item__end::before, .mdc-list-item--with-trailing-meta.mdc-list-item--with-two-lines .mdc-list-item__end::before {\n  display: inline-block;\n  width: 0;\n  height: 28px;\n  content: "";\n  vertical-align: 0;\n}\n\n.mdc-list-item--with-leading-radio .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n[dir=rtl] .mdc-list-item--with-leading-radio .mdc-list-item__start,\n[dir=rtl] .mdc-list-item--with-leading-checkbox .mdc-list-item__start {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n.mdc-list-item--with-leading-radio.mdc-list-item--with-two-lines .mdc-list-item__start,\n.mdc-list-item--with-leading-checkbox.mdc-list-item--with-two-lines .mdc-list-item__start {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-item--with-trailing-radio.mdc-list-item,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 16px;\n  padding-right: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item {\n  padding-left: 0;\n  padding-right: 16px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-left: 0;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-icon, [dir=rtl] .mdc-list-item--with-trailing-radio.mdc-list-item--with-leading-avatar,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-icon,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox.mdc-list-item--with-leading-avatar {\n  padding-right: 0;\n}\n.mdc-list-item--with-trailing-radio .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 24px;\n  margin-right: 8px;\n}\n[dir=rtl] .mdc-list-item--with-trailing-radio .mdc-list-item__end,\n[dir=rtl] .mdc-list-item--with-trailing-checkbox .mdc-list-item__end {\n  margin-left: 8px;\n  margin-right: 24px;\n}\n.mdc-list-item--with-trailing-radio.mdc-list-item--with-three-lines .mdc-list-item__end,\n.mdc-list-item--with-trailing-checkbox.mdc-list-item--with-three-lines .mdc-list-item__end {\n  align-self: flex-start;\n  margin-top: 8px;\n}\n\n.mdc-list-group__subheader {\n  margin: 0.75rem 16px;\n}\n\n.mdc-list-item--disabled .mdc-list-item__start,\n.mdc-list-item--disabled .mdc-list-item__content,\n.mdc-list-item--disabled .mdc-list-item__end {\n  opacity: 1;\n}\n.mdc-list-item--disabled .mdc-list-item__primary-text,\n.mdc-list-item--disabled .mdc-list-item__secondary-text {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n.mdc-list-item--disabled.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  color: var(--mat-list-list-item-disabled-leading-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-leading-icon-opacity, 0.38);\n}\n.mdc-list-item--disabled.mdc-list-item--with-trailing-icon .mdc-list-item__end {\n  color: var(--mat-list-list-item-disabled-trailing-icon-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-trailing-icon-opacity, 0.38);\n}\n\n.mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing, [dir=rtl] .mat-mdc-list-item.mat-mdc-list-item-both-leading-and-trailing {\n  padding-left: 0;\n  padding-right: 0;\n}\n\n.mdc-list-item.mdc-list-item--disabled .mdc-list-item__primary-text {\n  color: var(--mat-list-list-item-disabled-label-text-color, var(--mat-sys-on-surface));\n}\n\n.mdc-list-item:hover::before {\n  background-color: var(--mat-list-list-item-hover-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-hover-state-layer-opacity, var(--mat-sys-hover-state-layer-opacity));\n}\n\n.mdc-list-item.mdc-list-item--disabled::before {\n  background-color: var(--mat-list-list-item-disabled-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-disabled-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item:focus::before {\n  background-color: var(--mat-list-list-item-focus-state-layer-color, var(--mat-sys-on-surface));\n  opacity: var(--mat-list-list-item-focus-state-layer-opacity, var(--mat-sys-focus-state-layer-opacity));\n}\n\n.mdc-list-item--disabled .mdc-radio,\n.mdc-list-item--disabled .mdc-checkbox {\n  opacity: var(--mat-list-list-item-disabled-label-text-opacity, 0.3);\n}\n\n.mdc-list-item--with-leading-avatar .mat-mdc-list-item-avatar {\n  border-radius: var(--mat-list-list-item-leading-avatar-shape, var(--mat-sys-corner-full));\n  background-color: var(--mat-list-list-item-leading-avatar-color, var(--mat-sys-primary-container));\n}\n\n.mat-mdc-list-item-icon {\n  font-size: var(--mat-list-list-item-leading-icon-size, 24px);\n}\n\n@media (forced-colors: active) {\n  a.mdc-list-item--activated::after {\n    content: "";\n    position: absolute;\n    top: 50%;\n    right: 16px;\n    transform: translateY(-50%);\n    width: 10px;\n    height: 0;\n    border-bottom: solid 10px;\n    border-radius: 10px;\n  }\n  a.mdc-list-item--activated [dir=rtl]::after {\n    right: auto;\n    left: 16px;\n  }\n}\n\n.mat-mdc-list-base {\n  display: block;\n}\n.mat-mdc-list-base .mdc-list-item__start,\n.mat-mdc-list-base .mdc-list-item__end,\n.mat-mdc-list-base .mdc-list-item__content {\n  pointer-events: auto;\n}\n\n.mat-mdc-list-item,\n.mat-mdc-list-option {\n  width: 100%;\n  box-sizing: border-box;\n  -webkit-tap-highlight-color: transparent;\n}\n.mat-mdc-list-item:not(.mat-mdc-list-item-interactive),\n.mat-mdc-list-option:not(.mat-mdc-list-item-interactive) {\n  cursor: default;\n}\n.mat-mdc-list-item .mat-divider-inset,\n.mat-mdc-list-option .mat-divider-inset {\n  position: absolute;\n  left: 0;\n  right: 0;\n  bottom: 0;\n}\n.mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n.mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-left: 72px;\n}\n[dir=rtl] .mat-mdc-list-item .mat-mdc-list-item-avatar ~ .mat-divider-inset,\n[dir=rtl] .mat-mdc-list-option .mat-mdc-list-item-avatar ~ .mat-divider-inset {\n  margin-right: 72px;\n}\n\n.mat-mdc-list-item-interactive::before {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  content: "";\n  opacity: 0;\n  pointer-events: none;\n  border-radius: inherit;\n}\n\n.mat-mdc-list-item > .mat-focus-indicator {\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  position: absolute;\n  pointer-events: none;\n}\n.mat-mdc-list-item:focus-visible > .mat-focus-indicator::before {\n  content: "";\n}\n\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-line.mdc-list-item__secondary-text {\n  white-space: nowrap;\n  line-height: normal;\n}\n.mat-mdc-list-item.mdc-list-item--with-three-lines .mat-mdc-list-item-unscoped-content.mdc-list-item__secondary-text {\n  display: -webkit-box;\n  -webkit-box-orient: vertical;\n  -webkit-line-clamp: 2;\n}\n\nmat-action-list button {\n  background: none;\n  color: inherit;\n  border: none;\n  font: inherit;\n  outline: inherit;\n  -webkit-tap-highlight-color: transparent;\n  text-align: start;\n}\nmat-action-list button::-moz-focus-inner {\n  border: 0;\n}\n\n.mdc-list-item--with-leading-icon .mdc-list-item__start {\n  margin-inline-start: var(--mat-list-list-item-leading-icon-start-space, 16px);\n  margin-inline-end: var(--mat-list-list-item-leading-icon-end-space, 16px);\n}\n\n.mat-mdc-nav-list .mat-mdc-list-item {\n  border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n  --mat-focus-indicator-border-radius: var(--mat-list-active-indicator-shape, var(--mat-sys-corner-full));\n}\n.mat-mdc-nav-list .mat-mdc-list-item.mdc-list-item--activated {\n  background-color: var(--mat-list-active-indicator-color, var(--mat-sys-secondary-container));\n}\n']
    }]
  }], () => [], {
    _items: [{
      type: ContentChildren,
      args: [MatListOption, {
        descendants: true
      }]
    }],
    selectionChange: [{
      type: Output
    }],
    color: [{
      type: Input
    }],
    compareWith: [{
      type: Input
    }],
    multiple: [{
      type: Input
    }],
    hideSingleSelectionIndicator: [{
      type: Input
    }],
    disabled: [{
      type: Input
    }]
  });
})();
var MatListModule = class _MatListModule {
  static ɵfac = function MatListModule_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _MatListModule)();
  };
  static ɵmod = ɵɵdefineNgModule({
    type: _MatListModule,
    imports: [ObserversModule, MatRippleModule, MatPseudoCheckboxModule, MatList, MatActionList, MatNavList, MatSelectionList, MatListItem, MatListOption, MatListSubheaderCssMatStyler, MatListItemAvatar, MatListItemIcon, MatListItemLine, MatListItemTitle, MatListItemMeta],
    exports: [BidiModule, MatList, MatActionList, MatNavList, MatSelectionList, MatListItem, MatListOption, MatListItemAvatar, MatListItemIcon, MatListSubheaderCssMatStyler, MatDividerModule, MatListItemLine, MatListItemTitle, MatListItemMeta]
  });
  static ɵinj = ɵɵdefineInjector({
    imports: [ObserversModule, MatRippleModule, MatPseudoCheckboxModule, BidiModule, MatDividerModule]
  });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MatListModule, [{
    type: NgModule,
    args: [{
      imports: [ObserversModule, MatRippleModule, MatPseudoCheckboxModule, MatList, MatActionList, MatNavList, MatSelectionList, MatListItem, MatListOption, MatListSubheaderCssMatStyler, MatListItemAvatar, MatListItemIcon, MatListItemLine, MatListItemTitle, MatListItemMeta],
      exports: [BidiModule, MatList, MatActionList, MatNavList, MatSelectionList, MatListItem, MatListOption, MatListItemAvatar, MatListItemIcon, MatListSubheaderCssMatStyler, MatDividerModule, MatListItemLine, MatListItemTitle, MatListItemMeta]
    }]
  }], null, null);
})();
export {
  MAT_LIST,
  MAT_LIST_CONFIG,
  MAT_NAV_LIST,
  MAT_SELECTION_LIST_VALUE_ACCESSOR,
  MatActionList,
  MatDivider,
  MatList,
  MatListItem,
  MatListItemAvatar,
  MatListItemIcon,
  MatListItemLine,
  MatListItemMeta,
  MatListItemTitle,
  MatListModule,
  MatListOption,
  MatListSubheaderCssMatStyler,
  MatNavList,
  MatSelectionList,
  MatSelectionListChange,
  SELECTION_LIST,
  _MatListItemGraphicBase
};
//# sourceMappingURL=@angular_material_list.js.map
