# print 与 println：直接输出格式化文本

阅读前建议先了解：[C++20 format](../cpp20/format.md)。本篇介绍的新增能力属于 C++23。

## 从格式化字符串走到输出

C++20 的 std::format 先生成 string，再交给 cout 或文件输出。C++23 的 print/println 把格式化与输出结合，减少常见输出语句的组合。类型检查延续 format 的模型，不使用 printf 的可变参数格式匹配。

传统写法与新写法的关系如下：

```text
std::cout << std::format("answer={}", value) << '\n';
std::println("answer={}", value);
```

两者用于同样的文本输出需求，底层输出路径与错误处理并不完全相同，不应认为全局 I/O 设置都相同。

## 最小示例：换行由 println 完成

```cpp example id="cpp23-print" std="c++23" file="main.cpp" kind="single" compilers="all" output="answer=42" requires="__cpp_lib_print>=202207"
#include <print>
int main() {
    std::println("answer={}", 42);
}
```

println 追加换行，print 不追加。这里使用 C++23 支持的带格式字符串形式；不依赖无参数 std::println() 等后续增补接口，不能因新库允许就推断初版已支持。默认输出目的地是 stdout，也可使用 FILE* 重载指定文件。

## 格式检查与动态格式字符串

常规调用使用经过检查的格式字符串，整数与 `{}` 的类型匹配。错误示例只展示诊断，不作为可运行程序：

```text
std::println("{:d}", "text"); // 整数格式与字符串参数不匹配
```

C++23 的 print 接口不能直接把任意运行期 string 当作普通编译期格式参数。确需动态格式时，要选相应 vprint 接口和 make_format_args，并遵守参数存活要求；std::runtime_format 属于 C++26，不是此问题的 C++23 解法。

## 错误、编码与并发

格式化、分配或 I/O 都可能失败，print 不是 noexcept 日志设施。默认接口使用 C 标准输出流；不要假定 cout 的标志、宽度或 std::endl 的刷新效果同样作用于它。println 追加换行，不等于承诺每次刷新。

终端 Unicode 输出涉及普通字面量编码、环境与实现的终端路径，非终端文件输出仍需按格式和编码协议处理。本例只用 ASCII，使验证不依赖终端能力。并发日志若要求整个业务事件原子排列，应另外设计同步，不能把若干次 print 调用视作一条事务。

## 适用场景

适合命令行输出、简单报告和已有 format 格式的直接打印。需要流状态操作或自定义 ostream 协议时继续使用流；需要可靠日志、重试和结构化字段时，应明确自己的错误与同步边界。

选择 -std=c++23 不保证标准库带有 `<print>`，也不证明链接所需实现可用。支持宏满足后本仓库仍会实际编译链接与运行；这些阶段失败会报告错误而不是跳过。

## 权威资料

- [print 函数](https://eel.is/c++draft/print.fun)
- [P2093R14：Formatted output](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p2093r14.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/print.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
