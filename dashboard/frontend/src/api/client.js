import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getStats     = ()          => api.get('/stats')
export const getMarkets   = ()          => api.get('/markets')
export const getMarket    = (addr)      => api.get(`/markets/${addr}`)
export const getAgents    = ()          => api.get('/agents')
export const getTrades    = (limit=50)  => api.get(`/trades?limit=${limit}`)
export const getGovernance= ()          => api.get('/governance')
