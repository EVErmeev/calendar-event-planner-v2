# Установка в Windows (Calendar Event Planner)

Основная инструкция для пользователя.

## 1. Скачать installer

Скачайте `CalendarEventPlannerSetup-v1.1.0.exe` с страницы релиза.

Проверьте контрольную сумму:

```powershell
Get-FileHash .\CalendarEventPlannerSetup-v1.1.0.exe -Algorithm SHA256
```

Сравните со значением из `CalendarEventPlannerSetup-v1.1.0.exe.sha256`.

> Примечание: installer пока **не подписан** Authenticode (нет сертификата).
> Windows может показать предупреждение SmartScreen — это ожидаемо. Не
> имитируем цифровую подпись до появления сертификата.

## 2. Запустить installer

- Установка происходит в `%LOCALAPPDATA%\Programs\CalendarEventPlanner\`
  без прав администратора.
- Python, Git, OpenCode и skills устанавливать **не нужно** — всё включено.

## 3. Ввести EWS login/password

После первого запуска откроется мастер первоначальной настройки:

1. Введите корпоративный EWS endpoint, логин и пароль.
2. Нажмите «Проверить».

## 4. Пройти автоматическую проверку

Мастер выполнит:

- аутентификацию NTLM;
- сохранение пароля в Windows Credential Manager;
- поиск сотрудника по ФИО (EWS ResolveNames);
- подключение встроенного Exchange MCP;
- чтение календаря (read-only).

## 5. Начать работу

Нажмите «Начать работу». При следующем запуске пароль вводить не нужно.

## Требования

- Windows 10/11 x64.

## Порядок установки без мастера (диагностика)

```powershell
.\run_calendar_planner.bat --diagnostics
```