/**
 * Zignal Notifications System
 * HTTP-based notifications with polling
 * Version: 4.0
 */

class NotificationManager {
    constructor(options = {}) {
        this.options = {
            pollingInterval: options.pollingInterval || 30000, // 30 seconds
            notificationContainerId: options.notificationContainerId || 'notification-container',
            notificationListId: options.notificationListId || 'notification-list',
            notificationBadgeClass: options.notificationBadgeClass || 'notification-badge',
            notificationPopupClass: options.notificationPopupClass || 'notification-popup',
            soundEnabled: options.soundEnabled !== undefined ? options.soundEnabled : true,
            vibrationEnabled: options.vibrationEnabled !== undefined ? options.vibrationEnabled : true,
            maxPopupNotifications: options.maxPopupNotifications || 3,
            popupDuration: options.popupDuration || 5000,
            debug: options.debug || false,
        };

        this.notifications = [];
        this.unreadCount = 0;
        this.lastFetchTime = null;
        this.popupNotifications = [];
        this.notificationSound = new Audio('/static/sounds/notification.mp3');
        this.pollingTimer = null;

        // Initialize
        this._initializeUI();
        this.loadNotifications();
        this.startPolling();
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
    }

    /**
     * Start polling for new notifications
     */
    startPolling() {
        // Clear any existing timer
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
        }
        
        // Set up polling
        this.pollingTimer = setInterval(() => {
            this.checkForNewNotifications();
        }, this.options.pollingInterval);
        
        // Also check when the page becomes visible again
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.checkForNewNotifications();
            }
        });
        
        this._debug('Notification polling started');
    }

    /**
     * Check for new notifications
     */
    checkForNewNotifications() {
        // Special query parameter for checking only new notifications
        const timestamp = this.lastFetchTime ? new Date(this.lastFetchTime).toISOString() : '';
        const url = `/api/notifications/?since=${encodeURIComponent(timestamp)}`;
        
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
            // Update last fetch time
            this.lastFetchTime = new Date().toISOString();
            
            // Process new notifications
            if (data.notifications && data.notifications.length > 0) {
                // Add new notifications to the beginning of the list
                this.notifications = [...data.notifications, ...this.notifications];
                
                // Update unread count
                this.unreadCount = data.unread_count;
                
                // Update UI
                this._updateNotificationList();
                this._updateUnreadCount();
                
                // Show popup notifications for new items
                data.notifications.forEach(notification => {
                    this._showPopupNotification(notification);
                    
                    // Play sound for first notification only (if enabled)
                    if (this.options.soundEnabled && data.notifications.indexOf(notification) === 0) {
                        this.notificationSound.play().catch(e => {
                            this._debug('Error playing notification sound:', e);
                        });
                    }
                });
                
                // Vibrate if enabled (only once)
                if (this.options.vibrationEnabled && navigator.vibrate) {
                    navigator.vibrate(200);
                }
            } else {
                // Just update the unread count if it changed
                if (this.unreadCount !== data.unread_count) {
                    this.unreadCount = data.unread_count;
                    this._updateUnreadCount();
                }
            }
        })
        .catch(error => {
            this._debug('Error checking for new notifications:', error);
        });
    }

    /**
     * Load all notifications from API
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
            this.lastFetchTime = new Date().toISOString();
            
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
                // Mark all notifications as read locally
                this.notifications.forEach(notification => {
                    notification.unread = false;
                });
                
                // Update UI
                this.unreadCount = 0;
                this._updateNotificationList();
                this._updateUnreadCount();
            }
        })
        .catch(error => {
            this._debug('Error marking all notifications as read:', error);
        });
    }

    /**
     * Update notification as read in local data
     * @private
     * @param {string} notificationId - ID of the notification
     */
    _markNotificationAsRead(notificationId) {
        this.notifications.forEach(notification => {
            if (notification.id === notificationId) {
                notification.unread = false;
            }
        });
        
        this._updateNotificationList();
    }

    /**
     * Update notification list UI
     * @private
     */
    _updateNotificationList() {
        if (!this.notificationList) return;
        
        // Clear current list
        this.notificationList.innerHTML = '';
        
        if (this.notifications.length === 0) {
            // Show empty state
            const emptyItem = document.createElement('li');
            emptyItem.className = 'notification-empty';
            emptyItem.textContent = 'No notifications';
            this.notificationList.appendChild(emptyItem);
            return;
        }
        
        // Add notifications to list
        this.notifications.forEach(notification => {
            const listItem = document.createElement('li');
            listItem.className = 'notification-item';
            if (notification.unread) {
                listItem.classList.add('unread');
            }
            
            // Set data attributes
            listItem.dataset.id = notification.id;
            listItem.dataset.level = notification.level || 'info';
            
            // Create notification content
            const content = document.createElement('div');
            content.className = 'notification-content';
            
            // Add title
            const title = document.createElement('div');
            title.className = 'notification-title';
            title.textContent = notification.title;
            content.appendChild(title);
            
            // Add message
            const message = document.createElement('div');
            message.className = 'notification-message';
            message.textContent = notification.message;
            content.appendChild(message);
            
            // Add time
            const time = document.createElement('div');
            time.className = 'notification-time';
            time.textContent = this._formatDate(notification.created_at);
            content.appendChild(time);
            
            // Add action link if present
            if (notification.action_url) {
                const action = document.createElement('a');
                action.className = 'notification-action';
                action.href = notification.action_url;
                action.textContent = notification.action_text || 'View';
                content.appendChild(action);
            }
            
            listItem.appendChild(content);
            
            // Add click handler to mark as read
            if (notification.unread) {
                listItem.addEventListener('click', (e) => {
                    // Don't mark as read if clicking on action link
                    if (e.target.tagName !== 'A') {
                        this.markAsRead(notification.id);
                        
                        // Follow action URL if present
                        if (notification.action_url) {
                            window.location.href = notification.action_url;
                        }
                    }
                });
            }
            
            this.notificationList.appendChild(listItem);
        });
    }

    /**
     * Update unread notification count in UI
     * @private
     */
    _updateUnreadCount() {
        // Update all badge elements
        for (const element of this.notificationCountElements) {
            element.textContent = this.unreadCount > 0 ? this.unreadCount : '';
            element.style.display = this.unreadCount > 0 ? 'flex' : 'none';
        }
    }

    /**
     * Show popup notification
     * @private
     * @param {Object} notification - Notification data
     */
    _showPopupNotification(notification) {
        // Limit number of popups
        if (this.popupNotifications.length >= this.options.maxPopupNotifications) {
            const oldestPopup = this.popupNotifications.shift();
            this._removePopupNotification(oldestPopup);
        }
        
        // Create popup element
        const popup = document.createElement('div');
        popup.className = this.options.notificationPopupClass;
        popup.dataset.id = notification.id;
        popup.dataset.level = notification.level || 'info';
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'notification-popup-close';
        closeBtn.innerHTML = '×';
        closeBtn.addEventListener('click', () => {
            this._removePopupNotification(popup);
        });
        popup.appendChild(closeBtn);
        
        // Add content
        const content = document.createElement('div');
        content.className = 'notification-popup-content';
        
        const title = document.createElement('div');
        title.className = 'notification-popup-title';
        title.textContent = notification.title;
        content.appendChild(title);
        
        const message = document.createElement('div');
        message.className = 'notification-popup-message';
        message.textContent = notification.message;
        content.appendChild(message);
        
        popup.appendChild(content);
        
        // Add click handler
        popup.addEventListener('click', (e) => {
            if (e.target !== closeBtn && e.target !== closeBtn.firstChild) {
                this.markAsRead(notification.id);
                this._removePopupNotification(popup);
                
                // Follow action URL if present
                if (notification.action_url) {
                    window.location.href = notification.action_url;
                }
            }
        });
        
        // Add to document
        this.popupContainer.appendChild(popup);
        this.popupNotifications.push(popup);
        
        // Auto remove after duration
        setTimeout(() => {
            if (this.popupNotifications.includes(popup)) {
                this._removePopupNotification(popup);
            }
        }, this.options.popupDuration);
    }

    /**
     * Remove popup notification
     * @private
     * @param {HTMLElement} popup - Popup element to remove
     */
    _removePopupNotification(popup) {
        // Remove from DOM
        if (popup && popup.parentNode) {
            popup.parentNode.removeChild(popup);
        }
        
        // Remove from tracking array
        const index = this.popupNotifications.indexOf(popup);
        if (index !== -1) {
            this.popupNotifications.splice(index, 1);
        }
    }

    /**
     * Format date for display
     * @private
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    _formatDate(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // less than 1 minute
            return 'just now';
        } else if (diff < 3600000) { // less than 1 hour
            return `${Math.round(diff / 60000)} min ago`;
        } else if (diff < 86400000) { // less than 1 day
            return `${Math.round(diff / 3600000)} hours ago`;
        } else if (diff < 604800000) { // less than 1 week
            return `${Math.round(diff / 86400000)} days ago`;
        } else {
            return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        }
    }

    /**
     * Get CSRF token from cookie
     * @private
     * @returns {string} CSRF token
     */
    _getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Debug log
     * @private
     * @param {...*} args - Arguments to log
     */
    _debug(...args) {
        if (this.options.debug) {
            console.log('[NotificationManager]', ...args);
        }
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create global notification manager
    window.notificationManager = new NotificationManager({
        pollingInterval: 30000, // 30 seconds
        debug: false
    });
}); 