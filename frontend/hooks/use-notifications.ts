'use client'

import { useCallback, useEffect, useState } from 'react'

export type NotificationType = 'generation' | 'brand' | 'system'

export interface NotificationItem {
    id: string
    type: NotificationType
    title: string
    description: string
    time: string
    createdAt: string
    unread: boolean
}

const STORAGE_KEY = 'trendy.notifications'
const EVENT_NAME = 'trendy:notifications-changed'

function readNotifications(): NotificationItem[] {
    if (typeof window === 'undefined') return []
    try {
        const value = window.localStorage.getItem(STORAGE_KEY)
        return value ? JSON.parse(value) as NotificationItem[] : []
    } catch {
        return []
    }
}

function writeNotifications(items: NotificationItem[]) {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
    window.dispatchEvent(new Event(EVENT_NAME))
}

export function addNotification(notification: Omit<NotificationItem, 'id' | 'createdAt' | 'unread'>) {
    const item: NotificationItem = {
        ...notification,
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        createdAt: new Date().toISOString(),
        unread: true,
    }
    writeNotifications([item, ...readNotifications()])
    return item
}

export function addGenerationNotification(title: string, description: string, time = 'Just now') {
    return addNotification({ type: 'generation', title, description, time })
}

export function useNotifications() {
    const [notifications, setNotifications] = useState<NotificationItem[]>([])

    const refresh = useCallback(() => {
        setNotifications(readNotifications())
    }, [])

    useEffect(() => {
        refresh()
        window.addEventListener(EVENT_NAME, refresh)
        window.addEventListener('storage', refresh)
        return () => {
            window.removeEventListener(EVENT_NAME, refresh)
            window.removeEventListener('storage', refresh)
        }
    }, [refresh])

    const markAllAsRead = useCallback(() => {
        const updated = readNotifications().map((notification) => ({ ...notification, unread: false }))
        writeNotifications(updated)
    }, [])

    return { notifications, markAllAsRead, refresh }
}