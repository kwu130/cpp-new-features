# 带执行策略的算法

部分标准算法新增执行策略重载。`seq` 要求顺序执行，`par` 允许多线程，`par_unseq` 还允许线程内交错或向量化执行。

<!-- example id="cpp17-execution-policies" std="c++17" file="main.cpp" kind="single" compilers="gcc" output="1 4 9 16" -->
```cpp
#include <algorithm>
#include <execution>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3, 4};
    std::transform(std::execution::seq, values.begin(), values.end(), values.begin(),
                   [](int value) { return value * value; });
    for (const int value : values) {
        std::cout << value << (value == values.back() ? '\n' : ' ');
    }
}
```

示例使用 `seq` 以保持验证环境确定性；替换为并行策略前，回调必须避免数据竞争、锁顺序问题和对执行顺序的依赖。并行策略并不保证一定创建线程，实际收益需通过基准测试确认。

该示例由 CI 的 GCC/libstdc++ 任务验证。部分 libc++ 发行版本尚未提供标准执行策略，因此 Apple Clang 验证任务会明确跳过本例。

## 执行策略的语义

`sequenced_policy` 保证调用在当前线程按顺序执行。`parallel_policy` 允许在多个线程并行，但同一线程内调用不交错。`parallel_unsequenced_policy` 还允许向量化或线程内无序交错，因此回调不能执行不适合向量化的同步操作。

策略是“允许实现采用某种执行方式”，不是线程数量承诺。小输入、资源不足或实现限制都可能退回顺序执行。调用方不能通过观察线程 ID 推导正确性。

## 异常与终止

标准执行策略重载中的用户函数若抛异常，许多规定场景会调用 `std::terminate`，与普通无策略算法的异常传播不同。并行回调应把错误编码进结果或使用不会抛出的操作，并查阅具体算法和策略规则。

## 数据竞争与副作用

算法可以并发调用函数对象副本。不同迭代元素若写入共享计数器、日志容器或随机引擎，会产生竞争或锁瓶颈。安全模式是让每次调用只访问当前元素，或使用经过证明的归约算法和关联操作。

浮点加法不满足严格结合律，并行归约改变组合顺序后结果可能与顺序版本有微小差异。确定性和数值误差必须作为接口要求单独评估。

## 性能模型

并行化增加任务切分、调度、同步和缓存一致性成本。只有工作量、元素数量和计算/内存比例足够时才可能加速。错误共享会让不同核心反复争用同一缓存行；内存带宽饱和也会限制扩展。

## 示例与工程流程

示例使用 `seq` 验证策略重载接口及确定输出。迁移到 `par` 前，应先保证回调纯净和元素独立，再用真实数据基准测试顺序与并行版本，并在目标标准库上确认后端依赖和部署配置。

## 权威资料

- [P0024R2：并行算法](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0024r2.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
