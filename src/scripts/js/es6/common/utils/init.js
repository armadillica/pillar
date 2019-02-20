export { transformPlaceholder } from './placeholder'
export { prettyDate } from './prettydate'
export { getCurrentUser, initCurrentUser } from './currentuser'
export { thenLoadImage } from './files'


export function debounced(fn, delay=1000) {
    let timerId;
    return function (...args) {
      if (timerId) {
        clearTimeout(timerId);
      }
      timerId = setTimeout(() => {
        fn(...args);
        timerId = null;
      }, delay);
    }
  }

/**
 * Extracts error message from error of type String, Error or xhrError
 * @param {*} err 
 * @returns {String}
 */
export function messageFromError(err){
  if (typeof err === "string") {
    // type String
    return err;
  } else if(typeof err.message === "string") {
    // type Error
    return err.message;
  } else {
    // type xhr probably
    return xhrErrorResponseMessage(err);
  }
}
