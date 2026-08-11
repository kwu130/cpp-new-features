# `source_location`

`source_location` 以标准方式捕获调用点的文件、行号和函数名，适合日志、断言和诊断接口。

<!-- example id="cpp20-source-location" std="c++20" file="main.cpp" kind="single" compilers="all" output="message=ready, line-positive=true" -->
```cpp
#include <iostream>
#include <source_location>
#include <string_view>

void log(std::string_view message,
         const std::source_location location = std::source_location::current()) {
    std::cout << "message=" << message
              << ", line-positive=" << std::boolalpha << (location.line() > 0) << '\n';
}

int main() {
    log("ready");
}
```

默认参数必须在接口处调用 `current()` 才能取得调用者位置；若在函数体内调用，记录到的将是日志函数自身位置。文件路径可能包含构建环境信息，公开日志前应考虑脱敏。

## 捕获时机

`source_location::current()` 是特殊的静态工厂。用作默认实参时，它在调用表达式处形成位置，因此包装函数能看到调用者；在函数体普通语句中调用只会记录该语句自身。

对象通常保存文件名、函数名的静态字符串指针以及行列整数，复制廉价且不分配。标准不规定具体表示，也不保证列号或函数名格式在所有编译器一致。

四个主要观察接口是 `file_name()`、`function_name()`、`line()` 和 `column()`。字符串指针指向以零结尾的窄字符序列，内容由实现提供；行列返回无符号整数，column 在不能提供时可能为 0。

默认构造的 source_location 表示未知位置，各观察结果具有实现规定/空位置语义，不能假定行号必为有效源码行。只有来自 `current()` 的对象才应按调用位置解释。

### 多层包装必须转发

若 `trace()` 接收默认 location 后调用 `sink(message)` 而不传 location，sink 的默认参数捕获的是 trace 内调用点。要保留最外层调用者，每层包装都应接收并显式转发同一个 location。

<!-- example id="cpp20-source-location-forward" std="c++20" file="main.cpp" kind="single" compilers="all" output="caller-main=true" -->
```cpp
#include <iostream>
#include <source_location>
#include <string_view>

void sink(const std::source_location location) {
    const std::string_view function = location.function_name();
    std::cout << "caller-main=" << std::boolalpha
              << (function.find("main") != std::string_view::npos) << '\n';
}

void trace(const std::source_location location =
               std::source_location::current()) {
    sink(location);
}

int main() {
    trace();
}
```

默认参数在 `main` 的调用表达式求值，trace 再按值转发，所以 sink 观察到函数名包含 main。测试不比较完整函数名，因为编译器可以包含返回类型、签名或作用域等不同文本。

模板和内联不会改变抽象语义上的捕获位置，但函数名字符串可能展示实例化后的模板参数。优化器内联日志函数也不应让 location 自动变成机器码最终地址。

## 与预处理宏比较

传统 `__FILE__`、`__LINE__` 宏也捕获展开位置，但封装日志函数时常需要宏继续把调用点传入。`source_location` 可通过普通默认参数完成，保持类型检查、命名空间和函数重载能力。

宏仍可能用于编译器不支持的旧标准或要求调用点表达式文本的断言。两者混用时应统一日志字段格式。

宏能字符串化表达式、生成唯一标识并在预处理阶段条件展开，这是 source_location 不替代的能力。反过来，普通函数默认参数可参与重载、命名空间和模板，不会重复求值实参，也更容易单元测试显式传入位置。

兼容 C++17/20 的库常用条件编译：C++20 接收 source_location，旧版本由宏传 file/line。两条路径应归一成同一内部结构，避免日志后端到处出现预处理分支。

显式传 location 很适合测试或转发，但标准没有公共构造器让用户任意伪造文件和行号。测试日志格式时可只断言字段存在/范围，或把内部诊断位置抽象为可注入自有结构。

## 路径、可复现构建与隐私

`file_name()` 可能是绝对构建路径，泄露用户名、工作区或内部目录，并使不同机器构建产物不完全可复现。可通过编译器前缀映射选项、构建系统根路径裁剪或日志落盘前规范化处理。

函数名格式可能包含模板实参和编译器特有修饰，适合诊断但不应作为稳定协议键。行号也会随源码编辑变化，日志聚合最好搭配稳定事件 ID。

GCC/Clang 的前缀映射选项、MSVC 对应路径映射和构建系统 sandbox 可把绝对工作区统一成仓库相对路径。必须在编译阶段处理，因为 file_name 通常已经固化进二进制字符串表。

路径裁剪不能简单搜索最后一个目录名：不同平台分隔符、同名目录和生成源路径会导致误判。构建系统拥有源根映射，最适合统一处理；运行期后端再做最终白名单脱敏。

函数名可能显著增加二进制字符串体积，特别是深层模板实例化。高容量设备日志可把位置映射成构建期 ID，在符号服务器离线解析；标准 location 本身不提供这种压缩表。

外部 API 不应把 file/line 当授权或审计身份，调用者源码变化、插件工具链和显式转发都会改变值。它是诊断元数据，不是安全凭据。

## 日志接口设计

把 location 放在最后并提供 `current()` 默认值，是最常见调用形式。但参数包格式化日志很难在参数包后再放默认参数，常需包装对象、专门前端或宏；设计时要同时保留格式字符串编译期检查。

同步日志可立即复制 file/function 到输出。异步日志若只保存指针，通常依赖编译器提供静态存储字符串；为跨动态库卸载或插件边界安全，可能需要入队时复制或内部化字符串。

记录稳定事件 ID、时间、线程/任务 ID和 source_location 能互补：事件 ID支持聚合，位置支持源码定位。仅以行号做 dashboard key 会在每次编辑后分裂指标。

## 示例解析与实践

示例只验证行号为正，避免把具体行号写成脆弱输出。工程日志接口可按值接收默认 location，异步日志需复制字符串内容还是只保存静态指针要根据工具链保证审查，并对外部可见日志执行路径脱敏。

## 权威资料

- [P1208R6：source_location](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1208r6.pdf)
- [工作草案：source_location](https://eel.is/c++draft/support.srcloc)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
