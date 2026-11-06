import type { Hooks, VNode } from 'lib/view';

// Maia's MoveTooltip presentation, adapted to the native analysis DOM.
export interface MoveTooltipDetails {
  san: string;
  color: string;
  maiaProbability?: number;
  stockfishEval?: string;
  stockfishWinrate?: number;
  stockfishEvalLoss?: string;
}

let nextId = 0;
let hideActive: (() => void) | undefined;
const attachedTooltips = new WeakMap<HTMLElement | SVGElement, () => void>();
const dismissedTooltips = new WeakSet<HTMLElement | SVGElement>();

export function attachMoveTooltip(
  element: HTMLElement | SVGElement,
  details: () => MoveTooltipDetails | undefined,
): () => void {
  const id = `nosweat-move-tooltip-${++nextId}`;
  let popup: HTMLElement | undefined;
  let hovered = false;
  let focused = false;

  const hide = () => {
    popup?.remove();
    popup = undefined;
    const describedBy = element
      .getAttribute('aria-describedby')
      ?.split(/\s+/)
      .filter(value => value !== id);
    if (describedBy?.length) element.setAttribute('aria-describedby', describedBy.join(' '));
    else element.removeAttribute('aria-describedby');
    window.removeEventListener('scroll', hide, true);
    window.removeEventListener('resize', hide);
    window.removeEventListener('keydown', escape);
    if (hideActive === hide) hideActive = undefined;
  };
  const escape = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      dismissedTooltips.add(element);
      hide();
    }
  };
  const show = () => {
    if (dismissedTooltips.has(element) || popup || !element.isConnected) return;
    const data = details();
    if (!data) return;
    hideActive?.();
    popup = document.createElement('div');
    popup.className = 'nosweat-move-tooltip';
    popup.id = id;
    popup.setAttribute('role', 'tooltip');
    const header = document.createElement('div');
    header.className = 'nosweat-move-tooltip__header';
    header.textContent = data.san;
    header.style.color = data.color;
    popup.append(header);
    const rows = document.createElement('div');
    rows.className = 'nosweat-move-tooltip__rows';
    const row = (label: string, value: string, maia = false) => {
      const name = document.createElement('span');
      name.className = maia ? 'nosweat-move-tooltip__maia' : 'nosweat-move-tooltip__fish';
      name.textContent = label;
      const number = document.createElement('span');
      number.textContent = value;
      rows.append(name, number);
    };
    if (data.maiaProbability !== undefined)
      row('Maia:', `${(Math.round(data.maiaProbability * 1000) / 10).toFixed(1)}%`, true);
    if (data.stockfishEval !== undefined) row('SF Eval:', data.stockfishEval);
    if (data.stockfishWinrate !== undefined)
      row('SF Winrate:', `${(data.stockfishWinrate * 100).toFixed(1)}%`);
    if (data.stockfishEvalLoss !== undefined) row('SF Eval Loss:', data.stockfishEvalLoss);
    popup.append(rows);
    document.body.append(popup);
    const anchor = element.getBoundingClientRect();
    const box = popup.getBoundingClientRect();
    const maxLeft = Math.max(8, window.innerWidth - box.width - 8);
    const maxTop = Math.max(8, window.innerHeight - box.height - 8);
    popup.style.left = `${Math.min(maxLeft, Math.max(8, anchor.left))}px`;
    popup.style.top = `${Math.min(maxTop, Math.max(8, anchor.top >= box.height + 10 ? anchor.top - box.height - 10 : anchor.bottom + 10))}px`;
    const describedBy = element.getAttribute('aria-describedby');
    element.setAttribute('aria-describedby', [describedBy, id].filter(Boolean).join(' '));
    hideActive = hide;
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
    window.addEventListener('keydown', escape);
  };
  const enter = () => {
    hovered = true;
    dismissedTooltips.delete(element);
    show();
  };
  const leave = () => {
    hovered = false;
    if (!focused) hide();
  };
  const focus = () => {
    focused = true;
    dismissedTooltips.delete(element);
    show();
  };
  const blur = () => {
    focused = false;
    if (!hovered) hide();
  };
  element.addEventListener('mouseenter', enter);
  element.addEventListener('mouseleave', leave);
  element.addEventListener('focus', focus);
  element.addEventListener('blur', blur);
  focused = document.activeElement === element;
  hovered = element.matches(':hover');
  if (focused || hovered) show();

  return () => {
    hide();
    element.removeEventListener('mouseenter', enter);
    element.removeEventListener('mouseleave', leave);
    element.removeEventListener('focus', focus);
    element.removeEventListener('blur', blur);
  };
}

export function withMoveTooltip(hooks: Hooks, details: () => MoveTooltipDetails | undefined): Hooks {
  const attach = (vnode: VNode) => {
    const element = vnode.elm as HTMLElement | SVGElement;
    attachedTooltips.get(element)?.();
    attachedTooltips.set(element, attachMoveTooltip(element, details));
  };
  return {
    ...hooks,
    insert: vnode => {
      hooks.insert?.(vnode);
      attach(vnode);
    },
    update: (old, vnode) => {
      hooks.update?.(old, vnode);
      attach(vnode);
    },
    destroy: vnode => {
      const element = vnode.elm as HTMLElement | SVGElement;
      attachedTooltips.get(element)?.();
      attachedTooltips.delete(element);
      dismissedTooltips.delete(element);
      hooks.destroy?.(vnode);
    },
  };
}
