const KEY = 'jobmatch_token'

export function getToken() {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

function notify() {
  window.dispatchEvent(new Event('auth-change'))
}

export function setToken(token) {
  try {
    localStorage.setItem(KEY, token)
  } catch {
    
  }
  notify()
}

export function clearToken() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    
  }
  notify()
}
