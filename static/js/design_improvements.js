// ==========================================================================
// УЛУЧШЕНИЯ UI/UX - JavaScript для современного интерфейса
// ==========================================================================

// Плавная прокрутка к элементам
function smoothScrollTo(element) {
  element.scrollIntoView({ 
    behavior: 'smooth',
    block: 'center'
  });
}

// Анимация счётчиков
function animateCounter(element, start = 0, end = null, duration = 2000) {
  if (end === null) end = parseFloat(element.textContent) || 0;
  
  const range = end - start;
  const increment = end > start ? 1 : -1;
  const stepTime = Math.abs(Math.floor(duration / range));
  const startTime = Date.now();
  
  function updateCounter() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const current = start + (range * easeOutQuart(progress));
    
    element.textContent = end % 1 === 0 ? 
      Math.round(current).toLocaleString() : 
      current.toFixed(2);
    
    if (progress < 1) {
      requestAnimationFrame(updateCounter);
    }
  }
  
  updateCounter();
}

// Easing функция для плавной анимации
function easeOutQuart(t) {
  return 1 - (--t) * t * t * t;
}

// Инициализация анимаций при появлении элементов в видимой области
function initIntersectionObserver() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in-up');
        
        // Анимация счётчиков для метрик
        if (entry.target.classList.contains('metric-value')) {
          animateCounter(entry.target);
        }
        
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  // Наблюдаем за карточками и метриками
  document.querySelectorAll('.card-enhanced, .metric-card, .metric-value').forEach(el => {
    observer.observe(el);
  });
}

// Улучшенная система уведомлений
class NotificationSystem {
  constructor() {
    this.container = this.createContainer();
  }
  
  createContainer() {
    const container = document.createElement('div');
    container.className = 'notification-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      pointer-events: none;
    `;
    document.body.appendChild(container);
    return container;
  }
  
  show(message, type = 'info', duration = 4000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
      background: var(--gradient-card);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 1rem 1.5rem;
      margin-bottom: 10px;
      color: var(--fg);
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      backdrop-filter: blur(10px);
      pointer-events: auto;
      transform: translateX(400px);
      transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
      max-width: 350px;
      word-wrap: break-word;
    `;
    
    // Добавляем иконку в зависимости от типа
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 1.2rem;">${icons[type] || icons.info}</span>
        <span>${message}</span>
      </div>
    `;
    
    this.container.appendChild(notification);
    
    // Анимация появления
    requestAnimationFrame(() => {
      notification.style.transform = 'translateX(0)';
    });
    
    // Автоматическое скрытие
    setTimeout(() => {
      this.hide(notification);
    }, duration);
    
    // Скрытие по клику
    notification.addEventListener('click', () => {
      this.hide(notification);
    });
    
    return notification;
  }
  
  hide(notification) {
    notification.style.transform = 'translateX(400px)';
    notification.style.opacity = '0';
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }
}

// Система загрузки данных с индикацией
class LoadingSystem {
  static show(element, message = 'Загрузка...') {
    if (!element) return;
    
    element.dataset.originalContent = element.innerHTML;
    element.classList.add('loading-state');
    element.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; gap: 10px; opacity: 0.7;">
        <div class="spinner" style="
          width: 20px; 
          height: 20px; 
          border: 2px solid rgba(255,255,255,0.2);
          border-top: 2px solid var(--brand);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        "></div>
        <span>${message}</span>
      </div>
    `;
    
    // Добавляем анимацию спиннера если её нет
    if (!document.querySelector('#spinner-style')) {
      const style = document.createElement('style');
      style.id = 'spinner-style';
      style.textContent = `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }
  }
  
  static hide(element) {
    if (!element || !element.dataset.originalContent) return;
    
    element.classList.remove('loading-state');
    element.innerHTML = element.dataset.originalContent;
    delete element.dataset.originalContent;
  }
}

// Улучшенная обработка форм
function enhanceForms() {
  const forms = document.querySelectorAll('form');
  
  forms.forEach(form => {
    // Добавляем класс для стилизации
    form.classList.add('form-modern');
    
    // Обработчик отправки с индикацией загрузки
    form.addEventListener('submit', function(e) {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        LoadingSystem.show(submitBtn, 'Отправка...');
      }
    });
    
    // Валидация в реальном времени
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
      input.addEventListener('blur', function() {
        validateInput(this);
      });
      
      input.addEventListener('input', function() {
        clearValidationError(this);
      });
    });
  });
}

// Валидация полей ввода
function validateInput(input) {
  const value = input.value.trim();
  const isRequired = input.hasAttribute('required');
  
  clearValidationError(input);
  
  if (isRequired && !value) {
    showValidationError(input, 'Это поле обязательно для заполнения');
    return false;
  }
  
  // Специфичная валидация по типам
  if (input.type === 'email' && value) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      showValidationError(input, 'Введите корректный email адрес');
      return false;
    }
  }
  
  if (input.type === 'number' && value) {
    if (isNaN(value) || value < 0) {
      showValidationError(input, 'Введите корректное число');
      return false;
    }
  }
  
  return true;
}

function showValidationError(input, message) {
  input.classList.add('is-invalid');
  
  let errorDiv = input.parentNode.querySelector('.validation-error');
  if (!errorDiv) {
    errorDiv = document.createElement('div');
    errorDiv.className = 'validation-error';
    errorDiv.style.cssText = `
      color: var(--error-light);
      font-size: 0.85rem;
      margin-top: 0.25rem;
      font-weight: 500;
    `;
    input.parentNode.appendChild(errorDiv);
  }
  
  errorDiv.textContent = message;
}

function clearValidationError(input) {
  input.classList.remove('is-invalid');
  const errorDiv = input.parentNode.querySelector('.validation-error');
  if (errorDiv) {
    errorDiv.remove();
  }
}

// Система горячих клавиш
class HotkeysSystem {
  constructor() {
    this.shortcuts = new Map();
    this.init();
  }
  
  init() {
    document.addEventListener('keydown', (e) => {
      const key = this.getKeyString(e);
      const action = this.shortcuts.get(key);
      
      if (action && typeof action === 'function') {
        e.preventDefault();
        action(e);
      }
    });
  }
  
  getKeyString(event) {
    const parts = [];
    if (event.ctrlKey) parts.push('ctrl');
    if (event.altKey) parts.push('alt');
    if (event.shiftKey) parts.push('shift');
    parts.push(event.key.toLowerCase());
    return parts.join('+');
  }
  
  register(keyString, action) {
    this.shortcuts.set(keyString, action);
  }
  
  unregister(keyString) {
    this.shortcuts.delete(keyString);
  }
}

// Улучшенная работа с таблицами
function enhanceTables() {
  const tables = document.querySelectorAll('.table');
  
  tables.forEach(table => {
    table.classList.add('table-modern');
    
    // Добавляем сортировку по столбцам
    const headers = table.querySelectorAll('thead th');
    headers.forEach((header, index) => {
      if (!header.classList.contains('no-sort')) {
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';
        header.addEventListener('click', () => sortTable(table, index));
      }
    });
  });
}

function sortTable(table, column) {
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const isNumeric = rows.every(row => {
    const cell = row.cells[column];
    const text = cell.textContent.trim().replace(/[^\d.-]/g, '');
    return text === '' || !isNaN(parseFloat(text));
  });
  
  const sortedRows = rows.sort((a, b) => {
    const aText = a.cells[column].textContent.trim();
    const bText = b.cells[column].textContent.trim();
    
    if (isNumeric) {
      const aNum = parseFloat(aText.replace(/[^\d.-]/g, '')) || 0;
      const bNum = parseFloat(bText.replace(/[^\d.-]/g, '')) || 0;
      return aNum - bNum;
    } else {
      return aText.localeCompare(bText);
    }
  });
  
  // Очищаем tbody и добавляем отсортированные строки
  tbody.innerHTML = '';
  sortedRows.forEach(row => tbody.appendChild(row));
}

// Инициализация всех улучшений при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
  // Создаём глобальные экземпляры
  window.notifications = new NotificationSystem();
  window.hotkeys = new HotkeysSystem();
  
  // Инициализируем улучшения
  initIntersectionObserver();
  enhanceForms();
  enhanceTables();
  
  // Регистрируем горячие клавиши
  hotkeys.register('ctrl+/', () => {
    notifications.show('Доступные горячие клавиши:<br/>Ctrl+/ - показать справку<br/>Escape - закрыть модальные окна', 'info', 6000);
  });
  
  hotkeys.register('escape', () => {
    // Закрываем все модальные окна
    const modals = document.querySelectorAll('.modal.show');
    modals.forEach(modal => {
      const bootstrapModal = bootstrap.Modal.getInstance(modal);
      if (bootstrapModal) {
        bootstrapModal.hide();
      }
    });
  });
  
  // Улучшаем существующие элементы
  const cards = document.querySelectorAll('.card');
  cards.forEach(card => {
    if (!card.classList.contains('card-enhanced')) {
      card.classList.add('card-enhanced');
    }
  });
  
  // Заменяем стандартные кнопки на современные
  const buttons = document.querySelectorAll('.btn-primary, .btn-dark');
  buttons.forEach(btn => {
    btn.classList.add('btn-modern', 'primary');
  });
  
  // Обновляем статусные индикаторы
  const pills = document.querySelectorAll('.pill');
  pills.forEach(pill => {
    pill.classList.add('status-badge');
    const dot = pill.querySelector('.pill-dot');
    if (dot) {
      dot.classList.add('status-dot');
    }
  });
  
  console.log('🎨 Улучшения дизайна загружены успешно!');
});

// Экспорт для использования в других скриптах
window.DesignEnhancements = {
  LoadingSystem,
  NotificationSystem,
  HotkeysSystem,
  smoothScrollTo,
  animateCounter
};
