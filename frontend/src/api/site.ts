import { request, jsonRequest, id } from './client'
import type { Schema } from '../types/api'
export const getPublicSite = () => request<Schema<'PublicSiteView'>>('/api/v1/site/content')
export const getPublicCases = () => request<Schema<'PublicCaseView'>[]>('/api/v1/site/cases')
export const getAdminSiteContent = () => request<Schema<'SiteContentView'>>('/api/v1/admin/site/content')
export const updateSiteContent = (body: Schema<'SiteContentUpdate'>) => jsonRequest<Schema<'SiteContentView'>>('/api/v1/admin/site/content', 'PATCH', body)
export const getAdminCases = () => request<Schema<'AdminCaseView'>[]>('/api/v1/admin/site/cases')
export const publishCase = (body: Schema<'CasePublish'>) => jsonRequest<Schema<'AdminCaseView'>>('/api/v1/admin/site/cases', 'POST', body)
export const withdrawCase = (caseId: string, policyVersion: string) => jsonRequest<Schema<'AdminCaseView'>>(`/api/v1/admin/site/cases/${id(caseId)}/withdraw`, 'POST', {policy_version:policyVersion})
