let originalConfig = {};

// Load configuration on page load
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();

    // Auto-expand first section on mobile
    if (window.innerWidth <= 768) {
        const firstSection = document.querySelector('.collapsible-section');
        if (firstSection) {
            firstSection.classList.add('expanded');
        }
    } else {
        // Expand all sections on desktop
        document.querySelectorAll('.collapsible-section').forEach(section => {
            section.classList.add('expanded');
            const content = section.querySelector('.collapsible-content');
            if (content) {
                content.classList.add('expanded');
            }
        });
    }
});

function toggleSection(header) {
    const section = header.parentElement;
    const content = section.querySelector('.collapsible-content');
    const isExpanded = section.classList.contains('expanded');

    if (window.innerWidth <= 768) {
        // On mobile, close other sections first
        document.querySelectorAll('.collapsible-section').forEach(s => {
            if (s !== section) {
                s.classList.remove('expanded');
                s.querySelector('.collapsible-content').classList.remove('expanded');
            }
        });
    }

    // Toggle current section
    if (isExpanded) {
        section.classList.remove('expanded');
        content.classList.remove('expanded');
    } else {
        section.classList.add('expanded');
        content.classList.add('expanded');
    }
}

function toggleCheckbox(checkboxId) {
    const checkbox = document.getElementById(checkboxId);
    checkbox.checked = !checkbox.checked;

    // Visual feedback
    const group = checkbox.closest('.checkbox-group');
    group.style.transform = 'scale(0.98)';
    setTimeout(() => {
        group.style.transform = '';
    }, 150);
}

async function loadConfig() {
    try {
        const response = await fetch('/api/get_config');
        const result = await response.json();

        if (result.success) {
            originalConfig = JSON.parse(JSON.stringify(result.config)); // Deep copy
            populateForm(result.config);
            showNotification('Configuration loaded successfully', 'success');
        } else {
            showNotification('Failed to load configuration: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('Network error: ' + error.message, 'error');
    }
}

function populateForm(config) {
    // Settings checkboxes
    document.getElementById('motion_detection').checked = config.settings.motion_detection;
    document.getElementById('speech').checked = config.settings.speech;
    document.getElementById('webserver').checked = config.settings.webserver;
    document.getElementById('discord_notifications').checked = config.settings.discord_notifications;
    document.getElementById('discord_bot').checked = config.settings.discord_bot;
    document.getElementById('debug').checked = config.settings.debug;

    // Camera settings
    document.getElementById('main_camera').value = config.camera.main;
    document.getElementById('v_cam').value = config.camera.v_cam;
    document.getElementById('body_inc').value = config.camera.body_inc;
    document.getElementById('face_inc').value = config.camera.face_inc;
    document.getElementById('motion_inc').value = config.camera.motion_inc;
    document.getElementById('undetected_time').value = config.camera.undetected_time;
    document.getElementById('fallback_fps').value = config.camera.fallback_fps;

    // Discord settings
    document.getElementById('discord_webhook_url').value = config.discord.webhook_url;
    document.getElementById('discord_bot_token').value = config.discord.bot_token;
}

function resetForm() {
    populateForm(originalConfig);
    showNotification('Form reset to original values', 'success');
}

async function saveConfig() {
    const saveBtn = document.querySelector('.btn-save');
    saveBtn.classList.add('loading');
    saveBtn.style.position = 'relative';
    saveBtn.textContent = '💾 Saving...';

    try {
        const newConfig = {
            settings: {
                motion_detection: document.getElementById('motion_detection').checked,
                speech: document.getElementById('speech').checked,
                webserver: document.getElementById('webserver').checked,
                discord_notifications: document.getElementById('discord_notifications').checked,
                discord_bot: document.getElementById('discord_bot').checked,
                debug: document.getElementById('debug').checked
            },
            camera: {
                main: parseInt(document.getElementById('main_camera').value),
                v_cam: parseInt(document.getElementById('v_cam').value),
                body_inc: parseInt(document.getElementById('body_inc').value),
                face_inc: parseInt(document.getElementById('face_inc').value),
                motion_inc: parseInt(document.getElementById('motion_inc').value),
                undetected_time: parseInt(document.getElementById('undetected_time').value),
                fallback_fps: parseInt(document.getElementById('fallback_fps').value)
            },
            discord: {
                webhook_url: document.getElementById('discord_webhook_url').value,
                bot_token: document.getElementById('discord_bot_token').value
            }
        };

        // Validate required fields
        const requiredFields = ['main_camera', 'v_cam', 'body_inc', 'face_inc', 'motion_inc', 'undetected_time', 'fallback_fps'];
        const missingFields = requiredFields.filter(field => {
            const value = document.getElementById(field).value;
            return !value || isNaN(parseInt(value));
        });

        if (missingFields.length > 0) {
            showNotification('Please fill in all camera settings fields', 'error');
            return;
        }

        const response = await fetch('/api/save_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(newConfig)
        });

        const result = await response.json();

        if (result.success) {
            originalConfig = JSON.parse(JSON.stringify(newConfig)); // Update original
            showNotification('✅ Configuration saved! Restart system to apply changes', 'success');
        } else {
            showNotification('❌ Save failed: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('❌ Network error: ' + error.message, 'error');
    } finally {
        saveBtn.classList.remove('loading');
        saveBtn.style.position = '';
        saveBtn.textContent = '💾 Save';
    }
}

function showNotification(message, type) {
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => notification.classList.add('show'), 100);
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Handle window resize
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        // Desktop: expand all sections
        document.querySelectorAll('.collapsible-section').forEach(section => {
            section.classList.add('expanded');
            section.querySelector('.collapsible-content').classList.add('expanded');
        });
    }
});

// Handle orientation change
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        // Refresh layout after orientation change
        if (window.innerWidth <= 768) {
            document.querySelectorAll('.collapsible-section').forEach((section, index) => {
                if (index === 0) {
                    section.classList.add('expanded');
                    section.querySelector('.collapsible-content').classList.add('expanded');
                } else {
                    section.classList.remove('expanded');
                    section.querySelector('.collapsible-content').classList.remove('expanded');
                }
            });
        }
    }, 500);
});

// Prevent double-tap zoom on iOS
let lastTouchEnd = 0;
document.addEventListener('touchend', function (event) {
    const now = (new Date()).getTime();
    if (now - lastTouchEnd <= 300) {
        event.preventDefault();
    }
    lastTouchEnd = now;
}, false);

// Add haptic feedback for supported devices
function hapticFeedback() {
    if (navigator.vibrate) {
        navigator.vibrate(10);
    }
}

// Add haptic feedback to interactive elements
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.btn, .checkbox-group, .back-btn').forEach(element => {
        element.addEventListener('touchstart', hapticFeedback);
    });
});
