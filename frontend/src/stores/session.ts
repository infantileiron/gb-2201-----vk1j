import type {User} from '../types/entities';
export function savedUser():User|null {try{return JSON.parse(sessionStorage.getItem('cohort-user')||'null')}catch{return null}}
export function saveSession(token:string,user:User){sessionStorage.setItem('cohort-token',token);sessionStorage.setItem('cohort-user',JSON.stringify(user))}
export function clearSession(){sessionStorage.removeItem('cohort-token');sessionStorage.removeItem('cohort-user')}
