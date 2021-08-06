# library_storage

На данный момент скриптможно использовать для:
- нахождения дублирующихся/переименованных/перемещённых/удалённых/новых файлов
- выгрузки списка всех файлов и каталогов в csv и последующего поиска через текстовый редактор
- обмена списком имеющихся файлов с коллегами, чтобы понимать, у кого какой файл есть
- выгрузка diff-файла с описанием, какие файлы были переименованы/перемещёны/удалёны/добавлены, с добавленными файлами

План:
- [x] показ удалённых файлов
- [x] сохранение изменений в diff-файл
- [x] копирование новых файлов в diff-директорию
- [ ] применение diff-файла и диреткории
- [ ] экспорт в csv с учётом удалённых файлов
- [ ] показ изменённых файлов
- [ ] тесты
    - [ ] генерация csv
    - [ ] генерация diff
    - [ ] csv обновлённой базы должен совпасть с csv оригинальной базы + diff 
    - [ ] генерация csv с учётом удалённых файлов
- [ ] сделать скрипт с готовым конфигом для:
    - [ ] генерации csv оригинальной базы
    - [ ] выгрузки diff из изменённой базы
    - [ ] применения diff к оригинальной базе
- [ ] отмена diff-файла (откат изменений)
