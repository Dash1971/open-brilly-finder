import { type Hooks, type VNode } from 'lib/view/snabbdom';

// Native bind() installs only once. Candidate actions change as the report progresses.
export const reviewClick = (action: (event: MouseEvent) => void): Hooks => {
  const attach = (vnode: VNode) => {
    (vnode.elm as HTMLElement | SVGElement).onclick = action;
  };
  return { insert: attach, update: (_, vnode) => attach(vnode) };
};

// Use the native analysis hover for pointer and keyboard exploration without
// playing a move. Reattach after redraw so callbacks never retain an old report.
export const reviewMove = (action: (event: MouseEvent) => void, hover?: (active: boolean) => void): Hooks => {
  const attach = (vnode: VNode) => {
    const el = vnode.elm as HTMLElement | SVGElement;
    el.onclick = action;
    el.onmouseenter = el.onfocus = () => hover?.(true);
    el.onmouseleave = () => {
      if (document.activeElement !== el) hover?.(false);
    };
    el.onblur = () => {
      if (!el.matches(':hover')) hover?.(false);
    };
  };
  return {
    insert: attach,
    update: (_, vnode) => attach(vnode),
    destroy: vnode => {
      const el = vnode.elm as HTMLElement | SVGElement;
      if (document.activeElement === el || el.matches(':hover')) hover?.(false);
    },
  };
};
