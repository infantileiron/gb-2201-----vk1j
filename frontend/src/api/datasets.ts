import {request} from './client';
import type {Dataset,IngestBatchSummary} from '../types/entities';
export const list=()=>request<Dataset[]>('/datasets');
export const create=(data:unknown)=>request<Dataset>('/datasets','POST',data);
export const merge=(id:string,data:unknown)=>request<IngestBatchSummary>(`/datasets/${id}/ingest`,'POST',data);
export const batches=(id:string)=>request<IngestBatchSummary[]>(`/datasets/${id}/batches`);
export const allBatches=()=>request<IngestBatchSummary[]>('/ingest-batches');
