/**
 * Zignal Notifications System
 * Handles real-time notifications through WebSockets
 */

class NotificationManager {
    constructor(options = {}) {
        this.options = {
            wsUrl: options.wsUrl || this._getWebSocketUrl(),
            notificationContainerId: options.notificationContainerId || 'notification-container',
            notificationListId: options.notificationListId || 'notification-list',
            notificationCountId: options.notificationCountId || 'notification-count',
            notificationBadgeClass: options.notificationBadgeClass || 'notification-badge',
            notificationPopupClass: options.notificationPopupClass || 'notification-popup',
            soundEnabled: options.soundEnabled !== undefined ? options.soundEnabled : true,
            vibrationEnabled: options.vibrationEnabled !== undefined ? options.vibrationEnabled : true,
            maxPopupNotifications: options.maxPopupNotifications || 3,
            popupDuration: options.popupDuration || 5000,
            reconnectInterval: options.reconnectInterval || 3000,
            debug: options.debug || false,
        };

        this.socket = null;
        this.connected = false;
        this.connecting = false;
        this.notifications = [];
        this.unreadCount = 0;
        this.popupNotifications = [];
        this.notificationSound = new Audio('/static/sounds/notification.mp3');

        // Initialize
        this._initializeUI();
        this.connect();
    }

    /**
     * Initialize UI elements and event listeners
     * @private
     */
    _initializeUI() {
        // Find notification elements
        this.notificationContainer = document.getElementById(this.options.notificationContainerId);
        this.notificationList = document.getElementById(this.options.notificationListId);
        this.notificationCountElements = document.getElementsByClassName(this.options.notificationBadgeClass);

        // Create popup container if it doesn't exist
        this.popupContainer = document.createElement('div');
        this.popupContainer.className = 'notification-popup-container';
        this.popupContainer.style.position = 'fixed';
        this.popupContainer.style.top = '20px';
        this.popupContainer.style.right = '20px';
        this.popupContainer.style.zIndex = '9999';
        document.body.appendChild(this.popupContainer);

        // Add event listener for mark all as read button
        const markAllReadBtn = document.getElementById('mark-all-read-btn');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.markAllAsRead();
            });
        }

        // Load initial data
        this.loadNotifications();
    }

    /**
     * Get WebSocket URL based on current window location
     * @private
     * @returns {string} WebSocket URL
     */
    _getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/notifications/`;
    }

    /**
     * Connect to the WebSocket server
     */
    connect() {
        if (this.connected || this.connecting) return;
        
        this.connecting = true;
        this._debug('Connecting to WebSocket...');
        
        try {
            this.socket = new WebSocket(this.options.wsUrl);
            
            this.socket.onopen = () => {
                this.connected = true;
                this.connecting = false;
                this._debug('WebSocket connected');
            };
            
            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this._handleWebSocketMessage(data);
            };
            
            this.socket.onerror = (error) => {
                this._debug('WebSocket error:', error);
                this.connecting = false;
            };
            
            this.socket.onclose = () => {
                this.connected = false;
                this.connecting = false;
                this._debug('WebSocket disconnected. Reconnecting...');
                
                // Reconnect after delay
                setTimeout(() => this.connect(), this.options.reconnectInterval);
            };
        } catch (error) {
            this._debug('WebSocket connection error:', error);
            this.connecting = false;
            
            // Retry connection after delay
            setTimeout(() => this.connect(), this.options.reconnectInterval);
        }
    }

    /**
     * Handle WebSocket messages
     * @private
     * @param {Object} data - Message data
     */
    _handleWebSocketMessage(data) {
        this._debug('Received WebSocket message:', data);
        
        switch (data.type) {
            case 'notification':
                if (data.action === 'created') {
                    // Add new notification
                    this.notifications.unshift({
                        id: data.id,
                        title: data.title,
                        message: data.message,
                        level: data.level,
                        unread: true,
                        created_at: data.created_at,
                        action_url: data.action_url,
                        action_text: data.action_text
                    });
                    
                    // Update UI
                    this._updateNotificationList();
                    
                    // Show popup notification
                    this._showPopupNotification(data);
                    
                    // Play sound if enabled
                    if (this.options.soundEnabled) {
                        this.notificationSound.play().catch(e => {
                            this._debug('Error playing notification sound:', e);
                        });
                    }
                    
                    // Vibrate if enabled
                    if (this.options.vibrationEnabled && navigator.vibrate) {
                        navigator.vibrate(200);
                    }
                } else if (data.action === 'read') {
                    // Mark notification as read
                    this._markNotificationAsRead(data.id);
                }
                break;
                
            case 'unread_count':
                // Update unread count
                this.unreadCount = data.count;
                this._updateUnreadCount();
                break;
        }
    }

    /**
     * Load notifications from API
     * @param {boolean} unreadOnly - Whether to load only unread notifications
     */
    loadNotifications(unreadOnly = false) {
        const url = `/api/notifications/?unread_only=${unreadOnly}`;
        
        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            this.notifications = data.notifications;
            this.unreadCount = data.unread_count;
            
            this._updateNotificationList();
            this._updateUnreadCount();
        })
        .catch(error => {
            this._debug('Error loading notifications:', error);
        });
    }

    /**
     * Mark a notification as read
     * @param {string} notificationId - ID of the notification
     */
    markAsRead(notificationId) {
        if (!notificationId) return;
        
        // Send API request
        fetch(`/api/notifications/${notificationId}/mark-read/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this._getCsrfToken()
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this._markNotificationAsRead(notificationId);
                this.unreadCount = data.unread_count;
                this._updateUnreadCount();
            }
        })
        .catch(error => {
            this._debug('Error marking notification as read:', error);
        });
        
        // Also send WebSocket message
        if (this.connected) {
            this.socket.send(JSON.stringify({
                type: 'mark_read',
                id: notificationId
            }));
        }
    }

    /**
     * Mark all notifications as read
     */
    markAllAsRead() {
        // Send API request
        fetch('/api/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this._getCsrfToken()
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mark all as read in local data
                this.notifications.forEach(notification => {
                    notification.unread = false;
                });
                
                this.unreadCount = 0;
                this._updateNotificationList();
                this._updateUnreadCount();
            }
        })
        .catch(error => {
            this._debug('Error marking all notifications as read:', error);
        });
        
        // Also send WebSocket message
        if (this.connected) {
            this.socket.send(JSON.stringify({
                type: 'mark_all_read'
            }));
        }
    }

    /**
     * Mark a notification as read locally
     * @private
     * @param {string} notificationId - ID of the notification
     */
    _markNotificationAsRead(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification && notification.unread) {
            notification.unread = false;
            this._updateNotificationList();
        }
    }

    /**
     * Update the notification list UI
     * @private
     */
    _updateNotificationList() {
        if (!this.notificationList) return;
        
        // Clear current list
        this.notificationList.innerHTML = '';
        
        if (this.notifications.length === 0) {
            const emptyItem = document.createElement('li');
            emptyItem.className = 'notification-empty';
            emptyItem.textContent = 'No notifications';
            this.notificationList.appendChild(emptyItem);
            return;
        }
        
        // Add notifications
        this.notifications.forEach(notification => {
            const item = document.createElement('li');
            item.className = `notification-item ${notification.unread ? 'unread' : 'read'} level-${notification.level}`;
            item.setAttribute('data-id', notification.id);
            
            const content = document.createElement('div');
            content.className = 'notification-content';
            
            const title = document.createElement('div');
            title.className = 'notification-title';
            title.textContent = notification.title;
            
            const message = document.createElement('div');
            message.className = 'notification-message';
            message.textContent = notification.message;
            
            const meta = document.createElement('div');
            meta.className = 'notification-meta';
            
            const time = document.createElement('span');
            time.className = 'notification-time';
            time.textContent = this._formatDate(new Date(notification.created_at));
            
            content.appendChild(title);
            content.appendChild(message);
            
            meta.appendChild(time);
            
            if (notification.action_url && notification.action_text) {
                const action = document.createElement('a');
                action.className = 'notification-action';
                action.href = notification.action_url;
                action.textContent = notification.action_text;
                meta.appendChild(action);
            }
            
            content.appendChild(meta);
            item.appendChild(content);
            
            if (notification.unread) {
                const markReadBtn = document.createElement('button');
                markReadBtn.className = 'mark-read-btn';
                markReadBtn.innerHTML = '<span class="sr-only">Mark as read</span><i class="fas fa-check"></i>';
                markReadBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.markAsRead(notification.id);
                });
                item.appendChild(markReadBtn);
            }
            
            // Add click event to mark as read when clicked
            item.addEventListener('click', () => {
                if (notification.unread) {
                    this.markAsRead(notification.id);
                }
            });
            
            this.notificationList.appendChild(item);
        });
    }

    /**
     * Update unread count in UI
     * @private
     */
    _updateUnreadCount() {
        // Update count elements
        Array.from(this.notificationCountElements).forEach(element => {
            element.textContent = this.unreadCount;
            element.style.display = this.unreadCount > 0 ? 'inline-block' : 'none';
        });
    }

    /**
     * Show a popup notification
     * @private
     * @param {Object} notification - Notification data
     */
    _showPopupNotification(notification) {
        // Create popup element
        const popup = document.createElement('div');
        popup.className = `${this.options.notificationPopupClass} level-${notification.level}`;
        popup.setAttribute('data-id', notification.id);
        
        const title = document.createElement('div');
        title.className = 'popup-title';
        title.textContent = notification.title;
        
        const message = document.createElement('div');
        message.className = 'popup-message';
        message.textContent = notification.message;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'popup-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => {
            this._removePopupNotification(popup);
            this.markAsRead(notification.id);
        });
        
        popup.appendChild(closeBtn);
        popup.appendChild(title);
        popup.appendChild(message);
        
        if (notification.action_url && notification.action_text) {
            const action = document.createElement('a');
            action.className = 'popup-action';
            action.href = notification.action_url;
            action.textContent = notification.action_text;
            popup.appendChild(action);
        }
        
        // Add to popup container
        this.popupContainer.appendChild(popup);
        this.popupNotifications.push(popup);
        
        // Remove old popups if exceeding max
        while (this.popupNotifications.length > this.options.maxPopupNotifications) {
            const oldPopup = this.popupNotifications.shift();
            if (oldPopup && oldPopup.parentNode) {
                oldPopup.parentNode.removeChild(oldPopup);
            }
        }
        
        // Auto remove after duration
        setTimeout(() => {
            this._removePopupNotification(popup);
        }, this.options.popupDuration);
    }

    /**
     * Remove a popup notification
     * @private
     * @param {HTMLElement} popup - Popup element to remove
     */
    _removePopupNotification(popup) {
        if (popup && popup.parentNode) {
            popup.classList.add('fade-out');
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
                this.popupNotifications = this.popupNotifications.filter(p => p !== popup);
            }, 300);
        }
    }

    /**
     * Format date for display
     * @private
     * @param {Date} date - Date to format
     * @returns {string} Formatted date string
     */
    _formatDate(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        
        if (diff < 60) {
            return 'just now';
        } else if (diff < 3600) {
            const minutes = Math.floor(diff / 60);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else if (diff < 86400) {
            const hours = Math.floor(diff / 3600);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (diff < 604800) {
            const days = Math.floor(diff / 86400);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    /**
     * Get CSRF token from cookies
     * @private
     * @returns {string} CSRF token
     */
    _getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return '';
    }

    /**
     * Debug logging
     * @private
     */
    _debug(...args) {
        if (this.options.debug) {
            console.log('[NotificationManager]', ...args);
        }
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if user is logged in (check for presence of notification elements)
    if (document.getElementById('notification-container')) {
        window.notificationManager = new NotificationManager({
            debug: false
        });
    }
}); 