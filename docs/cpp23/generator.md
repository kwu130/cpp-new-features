# generator：标准库的同步协程序列

阅读前建议先了解：[C++20 协程](../cpp20/coroutines.md)、[Ranges](../cpp20/ranges.md)、[对象生命周期](../prerequisites.md#对象生命周期与引用)。本篇介绍的新增能力属于 C++23。

## 从手写 Promise 到标准生成器

C++20 提供协程语言机制，但逐个产出值需要自己定义 Promise、句柄包装、恢复与清理。C++23 的 std::generator 封装同步序列的这些协议，让业务函数只写 co_yield 和普通循环。

generator 是同步、惰性、单次遍历的序列。它没有自动线程、后台预取或 I/O 事件循环，不能拿它代替异步 task。

## 最小示例：按需取得三个整数

```cpp example id="cpp23-generator" std="c++23" file="main.cpp" kind="single" compilers="all" output="values=1 2 3" requires="__cpp_lib_generator>=202207"
#include <generator>
#include <iostream>
std::generator<int> sequence() {
    for (int value = 1; value <= 3; ++value) co_yield value;
}
int main() {
    auto values = sequence();
    bool first = true;
    std::cout << "values=";
    for (int value : values) {
        std::cout << (first ? "" : " ") << value;
        first = false;
    }
    std::cout << '\n';
}
```

调用 sequence() 建立生成器；遍历时逐个恢复到 co_yield，读当前值并继续推进。相较先构造 vector 返回，生成器不把全部结果物化；帧本身仍可能分配。传统 vector 可重复遍历，generator 不提供同样的多遍语义，两种行为不能视为完全等价。

## 单次遍历的契约

generator 建模 input_range，不是 forward_range。一个生成器对象的 begin() 不能反复调用来从头重放；需要多次遍历时调用 sequence() 创建新生成器，或把结果收集到容器。

生成器持有帧所有权，可移动、不可复制。不要再用 C++20 教学句柄包装器的 next() 方法访问它；标准 generator 使用 begin/end 与迭代器递增的范围协议。不要推进结束迭代器。

## 产出引用与生命周期

模板参数影响产出的引用与值类型。即使 generator<int> 看起来按整数生成，解引用结果也依赖当前产出及帧状态；本例循环按值复制整数，不把内部引用留到下一次推进之后。

可以用 generator<T&> 表达对外部元素的借用，但外部数据必须存活，generator 不取得所有权。协程函数的引用参数、成员函数对象和捕获式协程 Lambda 都仍有原来的生命周期陷阱；标准包装器不会延长引用目标寿命。

提前退出循环后，生成器最终析构会销毁帧，并清理仍存活的局部对象。异常可能在开始或递增恢复协程时传播，应在消费序列的边界处理；构造对象也可能因帧分配失败而抛异常。

## 组合与适用场景

适合逐条解析、按需遍历树或生成较大序列。ranges::elements_of 可用于委托另一个范围/生成器的产出，先理解单层寿命再学习嵌套；消费者仍沿同步调用栈推进。

若需随机访问、多遍遍历或保留所有结果，用容器更适合；异步等待外部事件需要其他协议。不要用“协程”一词推断线程安全，移动或消费同一序列时仍需遵守普通对象与同步规则。

部分标准库尚未实现 `<generator>`；支持宏不满足时本仓库明确跳过，不能把 C++20 手写 Generator 冒充此标准接口的验证。

## 权威资料

- [generator](https://eel.is/c++draft/coro.generator)
- [P2502R2：同步协程生成器](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p2502r2.pdf)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/generator.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
