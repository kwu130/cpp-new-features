# stacktrace：记录当前调用栈用于诊断

阅读前建议先了解：[异常与错误处理](../cpp11/core-utilities.md)、[对象与资源管理](../prerequisites.md#所有权与-raii)。本篇介绍的新增能力属于 C++23。

## 诊断缺少调用路径

source_location 能记录代码主动传入的调用点，但一次失败往往经过多个函数。传统方式依赖调试器或平台专属栈回溯接口；C++23 的 stacktrace 提供标准化的当前栈快照及查询接口。

它记录调用路径，不能代替业务错误类型、异常或日志上下文。先理解快照是可能不完整的诊断信息，再考虑把它附到错误记录。

## 最小示例：取得快照，不假定栈深度

```cpp example id="cpp23-stacktrace" std="c++23" file="main.cpp" kind="single" compilers="all" output="capture complete" requires="__cpp_lib_stacktrace>=202011"
#include <iostream>
#include <stacktrace>
std::stacktrace capture() { return std::stacktrace::current(); }
int main() {
    const auto trace = capture();
    for (const auto& entry : trace) {
        static_cast<void>(entry.description());
    }
    std::cout << "capture complete
";
}
```

这个程序验证获取与遍历接口，输出故意不比较函数名、文件、地址或深度，因为它们依赖实现、优化、符号与部署方式。空快照也是允许结果；本例通过不代表生产环境已经提供有用符号。

实际诊断可把 std::to_string(trace) 保存到日志，也可逐项查看 description()、source_file() 和 source_line()。没有相关信息时字段可以为空或为零；不要把字符串格式视为可稳定解析的协议。

## 获取时机决定内容

异常处理器中调用 current() 看到的是处理时的当前栈，抛出位置的栈可能已经展开。若要保存发生错误的位置，应在错误产生或抛出前明确捕获并附到错误对象；标准异常不会自动携带 stacktrace。

source_location 成本通常更小且位置由 API 传递，stacktrace 关注多层调用，两者互补。并不是每个正常返回都值得抓栈。

## 成本、失败与工具链

捕获与符号解析可能需要分配及平台支持，存在明显诊断开销。current() 的捕获接口有不抛保证，但资源不足可能得到空快照；描述转换、字符串生成等后续处理仍需按接口考虑异常与分配。

头文件和宏可用仍不保证链接环境已经完整。某些 libstdc++ 版本需要额外的栈回溯支持库，具体链接参数应按编译器官方文档与已安装库确定。本仓库保持通用验证命令，不猜测所有平台都需要同一个额外库；宏满足却链接失败会报告失败。

不能假定接口适合信号处理器或崩溃后任意状态下调用。线上栈信息可能包含路径和实现细节，输出策略应服从应用的日志边界；本教程不添加环境相关日志。

## 适用场景

适合调试报告、错误采集和测试失败诊断。对协议错误仍使用明确错误码或 expected；对性能敏感路径可延迟或按需捕获。若目标库暂不支持，使用现有调试工具，不能将其他接口的 fallback 编译成功计作 stacktrace 通过。

## 权威资料

- [stacktrace](https://eel.is/c++draft/stacktrace)
- [P0881R7：标准栈回溯](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p0881r7.html)
- [libstdc++ 官方实现状态](https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/stacktrace.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
