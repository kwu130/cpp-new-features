# Filesystem

`<filesystem>` 提供路径拼接、目录遍历和文件状态等跨平台接口，避免手写字符串路径与平台 API。

<!-- example id="cpp17-filesystem" std="c++17" file="main.cpp" kind="single" compilers="all" output="report.txt" -->
```cpp
#include <filesystem>
#include <iostream>

int main() {
    const std::filesystem::path directory = "reports";
    const std::filesystem::path file = directory / "daily" / "report.txt";
    std::cout << file.filename().string() << '\n';
}
```

路径应通过 `/` 运算符组合，不要手工拼接分隔符。真实文件操作可能失败，应使用异常接口或带 `std::error_code` 的重载处理权限、竞争和不存在等情况。

## `path` 不是普通字符串

`filesystem::path` 保存目标平台的原生路径表示，并提供根目录、文件名、扩展名等词法组件操作。`operator/` 按路径规则组合，若右侧是绝对路径，结果行为与简单字符串追加不同。

词法操作只处理字符结构，不访问文件系统。`lexically_normal` 可以消除可判定的 `.`、`..` 片段，但不会解析符号链接；`canonical` 会访问文件系统并要求路径存在。安全检查不能只做字符串前缀比较，因为规范化、符号链接和大小写规则可能改变真实目标。

<!-- example id="cpp17-filesystem-lexical" std="c++17" file="main.cpp" kind="single" compilers="all" output="reports/daily.txt|.txt" -->
```cpp
#include <filesystem>
#include <iostream>

int main() {
    const std::filesystem::path raw = "reports/./archive/../daily.txt";
    const std::filesystem::path normalized = raw.lexically_normal();
    std::cout << normalized.generic_string() << '|'
              << normalized.extension().string() << '\n';
}
```

示例完全不访问磁盘：`lexically_normal` 只按路径语法消去 `.` 和可配对的 `archive/..`，`generic_string` 使用通用格式分隔符输出。若中间组件在真实文件系统上是符号链接，这个词法结果不一定与解析链接后的实际位置相同。

### 路径组成与替换接口

`root_name`、`root_directory`、`root_path`、`relative_path`、`parent_path`、`filename`、`stem` 和 `extension` 从语法层分解路径。点文件、末尾点号和多重扩展名的结果可能与业务直觉不同，例如压缩包的“完整扩展名”并非由单次 `extension()` 自动识别。

`replace_filename`、`replace_extension`、`remove_filename` 会修改路径对象本身。`operator/=` 追加路径组件，而 `operator+=` 是原生字符串级连接，两者不应混用：前者表达目录层级，后者只适合确实要扩展当前文件名文本的场景。

绝对路径、相对路径和带根名路径的组合受平台路径语法影响。可移植代码使用组件接口表达意图，不通过检查首字符是否为 `/` 来判断绝对路径。

## 查询与竞态

`exists`、`is_directory` 等状态查询只能描述查询瞬间。检查后到打开前，另一个进程可能替换或删除路径，这是典型 TOCTOU 竞态。安全敏感操作应尽量使用操作系统提供的原子打开策略，而不是依赖先检查后操作。

目录迭代器按需访问文件系统，顺序未指定，遍历期间目录变化的可见性也受实现影响。需要稳定输出时收集路径后显式排序，并决定权限错误是中止还是跳过。

`directory_iterator` 只遍历一层，`recursive_directory_iterator` 递归进入子目录，并提供 `depth()`、`disable_recursion_pending()` 等控制接口。符号链接是否跟随由选项决定；错误的策略可能造成越界访问、重复遍历，甚至通过链接形成逻辑环。

迭代器是面向外部状态的输入式抽象，不应假设能像内存容器迭代器一样多次稳定遍历。每个 `directory_entry` 可缓存部分状态信息，但文件仍可能在查询与使用之间改变。

文件大小、最后写入时间、硬链接数、空间容量和权限都可能因平台、文件系统种类及权限而失败。返回的 `file_time_type` 时钟也不保证就是 `system_clock`，C++17 中不应直接假定能无损转成普通日历时间。

### `status`、`symlink_status` 与 `directory_entry`

`status(path)` 查询跟随符号链接后的目标状态，`symlink_status(path)` 查询链接本身。判断链接、常规文件和目录时必须先决定要观察哪一层；例如清理工具若先跟随链接再递归，可能离开原目录树。`file_status` 把文件类型和权限位打包，但“未知”“不存在”和查询失败不是同一业务状态，应结合错误码解释。

`directory_entry` 保存路径并允许查询状态、大小和时间。实现可以缓存某些信息以减少系统调用，但缓存的存在和新鲜程度不能当作一致性保证。执行真正操作前仍要接受文件已变化的事实，必要时直接操作打开的文件描述符或平台句柄。

`directory_options::skip_permission_denied` 可以让遍历跳过部分权限错误，`follow_directory_symlink` 则允许递归跟随目录链接。两者解决不同问题：前者控制恢复策略，后者改变遍历图。跟随链接时还要自行考虑环、重复节点和信任边界。

## 错误处理

多数操作提供抛出 `filesystem_error` 的重载和写入 `error_code` 的重载。异常形式适合失败即中止的高层流程；错误码形式适合批处理逐项恢复。忽略错误码会把权限、路径过长和设备故障误判为普通“不存在”。

使用错误码重载时，应在每次调用后检查 `ec`。某些函数用返回值表达正常的“没有发生”或布尔结果，错误则单独写入 `ec`；不能只看返回值。复用同一个 `error_code` 对象是允许的，成功调用会按相应接口约定清除它，但最清晰的代码仍在紧邻调用处处理结果。

`filesystem_error` 可携带操作描述、错误码以及一个或两个相关路径。高层日志应保留这些结构化信息，同时避免把不可信路径原样拼进终端控制序列或安全敏感输出。

## 创建、复制、重命名和删除

`create_directory` 创建单层目录，`create_directories` 尝试创建缺失的父层级；并发进程可能同时创建同一路径，调用方应按最终结果和错误码判断，而不是假定自己是唯一操作者。`copy` 的行为由 `copy_options` 控制，包括递归、覆盖、跳过和符号链接策略，冲突选项会导致未定义或错误的请求语义。

`rename` 能否原子完成、是否允许跨文件系统移动、目标存在时如何处理，都受平台影响。需要可靠替换配置文件时，应研究目标平台的原子重命名保证、刷盘顺序和崩溃一致性，标准路径接口本身不会构成完整事务。

`remove` 删除单个文件或空目录，`remove_all` 递归删除并返回删除数量。递归删除是高风险操作：必须先解析并验证精确目标，明确符号链接策略，禁止对空路径、根目录或未经信任的广泛路径执行。

### 权限、链接与空间信息

`permissions` 修改的是标准抽象中的权限位，并通过 `perm_options::replace`、`add` 或 `remove` 指定更新方式。权限模型在不同系统并不完全等价，ACL、继承规则、umask 和只读属性可能无法由这组位完整表达；它不是跨平台安全策略语言。

`create_hard_link` 与 `create_symlink` 的语义、所需权限以及是否支持目录链接均依赖平台。硬链接共享同一文件实体，符号链接保存另一路径；复制或删除工具必须明确是处理链接本身还是其目标。`hard_link_count` 也不能直接解释为“有多少业务文件名仍可访问”，因为并发和权限会影响观察。

`space(path)` 返回容量、可用空间和普通用户可用空间。值可能因配额、稀疏文件、压缩、网络文件系统和并发写入迅速变化，只适合提示或预检，不能保证后续写入成功。磁盘写入仍需处理短写、空间耗尽和同步失败。

### 当前目录与绝对化

`current_path()` 读取或设置进程当前工作目录。设置它会影响进程中其他线程解析相对路径的结果，因此库代码通常不应把“临时切换目录”当作局部操作。更稳健的设计是在入口解析明确基准目录，随后传递绝对路径或基准对象。

`absolute` 把路径相对某个基准转成绝对形式，但不等于规范化真实对象；`canonical` 要求组件存在并解析链接，`weakly_canonical` 允许尾部部分不存在。三者的选择取决于是在生成未来路径、显示路径，还是识别已有文件，不能互相替代。

## 编码与可移植性

原生路径字符类型在 POSIX 和 Windows 不同，字符串转换可能涉及编码。不要假设 `.string()` 永远是 UTF-8，也不要把平台特定分隔符写进业务格式。持久化或网络协议应定义独立于本机路径的编码与分隔规则。

`generic_string()` 提供通用格式表示，但字符编码问题仍需单独处理。`u8path` 是 C++17 接收 UTF-8 字节序列的适配入口；不同标准版本对 `char8_t` 的引入会改变相关重载类型，跨 C++17/C++20 共用代码需专门测试。

路径比较按路径的词法元素规则进行，不等于询问两个路径是否指向同一文件。`equivalent` 会访问文件系统判断现有路径的等价性，但仍可能失败；大小写不敏感、硬链接、符号链接和挂载点都使纯字符串比较不足。

## 示例解析与实践

示例只做纯词法组合，所以不依赖当前目录是否存在。实际工程应明确相对路径基准、符号链接策略、错误恢复、遍历顺序和信任边界，再执行读写。

## 权威资料

- [P0218R1：Filesystem](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0218r1.html)
- [工作草案：Filesystem library](https://eel.is/c++draft/filesystems)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
