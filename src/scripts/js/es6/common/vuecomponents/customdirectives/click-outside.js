/**
 * Directive to detect clicks outside of component.
 * Code from https://stackoverflow.com/a/42389266
 *
 * @example
 * <div
 *    v-click-outside="()=>{console.log('User clicked outside component')}"
 * >
 *    ...
 * </div>
 */
Vue.directive('click-outside', {
    bind: function (el, binding, vnode) {
      el.clickOutsideEvent = function (event) {
        // here I check that click was outside the el and his childrens
        if (!(el == event.target || el.contains(event.target))) {
          // and if it did, call method provided in attribute value
          vnode.context[binding.expression](event);
        }
      };
      document.body.addEventListener('click', el.clickOutsideEvent)
    },
    unbind: function (el) {
      document.body.removeEventListener('click', el.clickOutsideEvent)
    },
  });
