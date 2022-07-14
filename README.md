# Library Storage

На данный момент скриптможно использовать для:
- нахождения дублирующихся/переименованных/перемещённых/удалённых/новых файлов
- выгрузки списка всех файлов и каталогов в csv и последующего поиска через текстовый редактор
- обмена списком имеющихся файлов с коллегами, чтобы понимать, у кого какой файл есть
- выгрузка diff-файла с описанием, какие файлы были переименованы/перемещёны/удалёны/добавлены, с добавленными файлами

## Roadmap

- [x] показ удалённых файлов
- [x] сохранение изменений в diff-файл
- [x] копирование новых файлов в diff-директорию
- [x] применение diff-файла и диреткории
- [x] экспорт в csv с учётом удалённых файлов
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

## Using

1. Просканируйте оригинальное хранилище:
    ```sh
    syeysk-stor scan --path <path/to/original_storage> --struct <struct.csv>
    ```
    где `--path` - оригинальное хранилище, которое будет просканировано, `--struct` - файл, куда запишется структура хранилища.

2. Просканируйте копию хранилища (в которую Вы могли добавить новые файлы):
    ```sh
    syeysk-stor makediff --path <path/to/copy_storage> --struct <struct.csv> --diff <diff_of_copy_storage>
    ```
    где `--path` - копия хранилища, `--struct` - файл со структурой оригинального хранилища, `--diff` - куда запишется diff-файл с изменениями в копии относительно оригинала 

3. Примените изменния из копии хранилища в оригинальное хранилище:
    ```sh
    syeysk-stor applydiff --path <path/to/original_storage> --diff <diff_of_copy_storage>
    ```
    где `--path` - оригинальное хранилище, `--diff` - diff-файл копии хранилища

После этого оринальное хранилище будет соответствовать копии.
