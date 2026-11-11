import {request} from './client';
import type {Cohort} from '../types/entities';
export const list=()=>request<Cohort[]>('/cohorts');
export const create=(data:unknown)=>request<Cohort>('/cohorts','POST',data);
