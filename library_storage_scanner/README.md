# LibraryStorageScanner - Сканер хранилища книг

## Как работает программа

### Сканирование оригинального хранилища

Сканирование выполняет метод `scan_to_db` класса `LibraryStorage`. Перед сканированиевсе файлов всем находящимся файлам в базе данных проставляется флаг удалённости.

При добавлении/переименовании/удалении/перемещении в оригинальном хранилище допустимо его просканировать повторно.
В процессе сканирования при обнаружении:
- дубликата по хешу и пути - ничего не произойдёт, так как это тот же файл.
- нового файла - он добавится в базу данных
- перименованного/перемещённого файла - обновит в базе данных запись о нём

Удалённые с диска файлы не удаляются из базы данных. Если это сделать, то при добавлении вновь он изменит свой идентификатор, что сделает в заметках ссылки на него невалидными.
Также, если изменить файл, то он воспримется как новый, а старая версия файла будет считаться удалённой, при этом в базе останется запись об этой версии.

### Сканирование копии хранилища

В процессе сканирования при обнаружении:
- дубликата по хешу (с любым именем и путём) - ничего не произойдёт, так как любой дубль нам не нужен.
- нового файла - он добавится в базу данных

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