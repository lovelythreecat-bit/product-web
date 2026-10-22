import type { Schema } from '../types/api'
import { request, jsonRequest } from './client'
export const register = (body: Schema<'RegisterRequest'>) => jsonRequest<Schema<'AuthView'>>('/api/v1/auth/register','POST',body)
export const login = (body: Schema<'LoginRequest'>) => jsonRequest<Schema<'AuthView'>>('/api/v1/auth/login','POST',body)
export const logout = () => request<void>('/api/v1/auth/logout',{method:'POST'})
export const changePassword = (body: Schema<'PasswordChangeRequest'>) => jsonRequest<void>('/api/v1/auth/password','POST',body)
export const getProfile = (signal?:AbortSignal) => request<Schema<'ProfileView'>>('/api/v1/me',{signal})
export const updateProfile = (body: Schema<'ProfileUpdate'>) => jsonRequest<Schema<'ProfileView'>>('/api/v1/me','PATCH',body)
