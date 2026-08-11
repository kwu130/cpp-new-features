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

`current()` 在默认实参中的特殊捕获依赖求值点，而不是函数声明文本简单展开宏。显式传入另一个 location 会完全替代默认值，因此测试、代理层和错误转发可以保留原始产生位置。

行号与列号的基准按实现提供的源位置表示，预处理生成文件、`#line` 指令和编译器映射都会影响结果。不要用 column 精确值作为跨编译器测试断言，很多实现或构建模式可能返回 0。

文件名与函数名返回的 C 字符串由实现提供并具有足以供 location 使用的存储，但具体拼写不标准化。函数名可能包含模板实参、限定符、调用约定或编译器格式，适合人类诊断而不适合作为机器协议解析输入。

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

宏包装常能把 location 放在可变参数之前/之外，解决“参数包后无法自然追加默认实参”的接口形状，但宏应只捕获位置并立刻调用类型安全函数。不要在宏里重复求值消息参数，也不要让宏与函数版本产生不同过滤或格式化语义。

模板包装器若默认参数跟在普通形参后通常工作良好；完美转发参数包的日志函数则难以让编译器区分最后一个业务参数与 location。可使用一个包含 location 的前端对象、显式 `log_at(location, ...)` 内核，或有限宏薄层，而不是让每个调用者手写位置。

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

### 错误传播应保留产生点

底层函数创建错误对象时捕获 location，上层添加上下文时应保留原位置并另存包装位置，而不是覆盖同一字段。一个诊断往往同时需要“错误最初发生在哪里”和“在哪条业务路径被传播”，单个 location 不应承担完整堆栈追踪。

source_location 不抓取调用栈、模块名、二进制偏移或线程信息。它的成本低正因为只记录一个编译期位置。崩溃分析仍需 stack trace/symbolizer，分布式请求仍需 trace/span ID，不能用源码行号替代这些动态上下文。

异步边界应在提交任务时捕获调用者位置，而不是等工作线程执行日志函数时再调用 current。后者只会得到任务执行器内部位置。把 location 与拥有的消息数据一起入队，能在执行时间推迟时仍保留提交点。

## 示例解析与实践

示例只验证行号为正，避免把具体行号写成脆弱输出。工程日志接口可按值接收默认 location，异步日志需复制字符串内容还是只保存静态指针要根据工具链保证审查，并对外部可见日志执行路径脱敏。

## 位置字段速查

| 接口/模式 | 关键语义 |
| --- | --- |
| `current()` 默认实参 | 捕获调用表达式位置 |
| 函数体内 `current()` | 捕获包装函数自身当前语句位置 |
| `file_name()` | 实现提供路径，可能泄露构建根目录 |
| `function_name()` | 实现定义拼写，不可作稳定协议键 |
| `line()` | 源行号，受 #line/生成源影响 |
| `column()` | 实现可能无法提供并返回 0 |
| 默认构造 | 未知位置，不应假定字段有效 |
| 多层包装 | 每层显式转发原 location 防止覆盖 |
| 异步任务 | 应在提交点捕获，而非工作线程执行点 |
| 稳定聚合 | 配合事件 ID，勿仅按源码行聚合日志 |

## Source location 专项审查问题

- current() 是否写在默认参数而不是包装函数体？
- 多层包装是否始终显式转发最外层 location？
- 异步日志是否在提交点捕获而非执行点捕获？
- file_name 是否含绝对工作区、用户名或内部目录？
- 构建是否使用前缀映射保证路径脱敏和可复现？
- function_name 是否被错误解析为稳定协议字段？
- 测试是否避免断言精确列号和完整函数名？
- 事件聚合是否另有稳定 ID，而非只用易变行号？
- 插件卸载后异步队列是否还保存来源字符串指针？
- 错误传播是否同时保留原始发生点与包装上下文？

## 权威资料

- [P1208R6：source_location](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1208r6.pdf)
- [工作草案：source_location](https://eel.is/c++draft/support.srcloc)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
