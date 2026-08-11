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

## 查询与竞态

`exists`、`is_directory` 等状态查询只能描述查询瞬间。检查后到打开前，另一个进程可能替换或删除路径，这是典型 TOCTOU 竞态。安全敏感操作应尽量使用操作系统提供的原子打开策略，而不是依赖先检查后操作。

目录迭代器按需访问文件系统，顺序未指定，遍历期间目录变化的可见性也受实现影响。需要稳定输出时收集路径后显式排序，并决定权限错误是中止还是跳过。

## 错误处理

多数操作提供抛出 `filesystem_error` 的重载和写入 `error_code` 的重载。异常形式适合失败即中止的高层流程；错误码形式适合批处理逐项恢复。忽略错误码会把权限、路径过长和设备故障误判为普通“不存在”。

## 编码与可移植性

原生路径字符类型在 POSIX 和 Windows 不同，字符串转换可能涉及编码。不要假设 `.string()` 永远是 UTF-8，也不要把平台特定分隔符写进业务格式。持久化或网络协议应定义独立于本机路径的编码与分隔规则。

## 示例解析与实践

示例只做纯词法组合，所以不依赖当前目录是否存在。实际工程应明确相对路径基准、符号链接策略、错误恢复、遍历顺序和信任边界，再执行读写。
