# Vue components
[Vue.js](https://vuejs.org/) is a javascript framework for writing interactive ui components.
Vue.js is packed into tutti.js, and hence available site wide.

### Absolute must read
- https://vuejs.org/v2/api/#Options-Data
- https://vuejs.org/v2/api/#v-bind
- https://vuejs.org/v2/api/#v-model
- https://vuejs.org/v2/guide/conditional.html
- https://vuejs.org/v2/guide/list.html#v-for-with-an-Object
- https://vuejs.org/v2/api/#vm-emit
- https://vuejs.org/v2/api/#v-on

### Styling and animation of components
- https://vuejs.org/v2/guide/class-and-style.html#Binding-HTML-Classes
- https://vuejs.org/v2/guide/transitions.html

### More advanced, but important topics
- https://vuejs.org/v2/api/#is
- https://vuejs.org/v2/guide/components-slots.html#Slot-Content
- https://vuejs.org/v2/guide/mixins.html

### Rule of thumbs
- [Have a dash in your component name](https://vuejs.org/v2/guide/components-registration.html#Component-Names)
- Have one prop binding per line in component templates.
~~~
// Good! 
<my-component
	:propA="propX"
	:propB="propY"
/>

// Bad! 
<my-component :propA="propX" :propB="propY"/>
~~~
