# Ranges 与 Views

Ranges 算法直接接受范围；Views 则以惰性、非拥有方式组合过滤和转换，管道语法让数据流更清晰。

<!-- example id="cpp20-ranges" std="c++20" file="main.cpp" kind="single" compilers="all" output="4 16" -->
```cpp
#include <iostream>
#include <ranges>
#include <vector>

int main() {
    const std::vector<int> values{1, 2, 3, 4, 5};
    auto squares = values
        | std::views::filter([](int value) { return value % 2 == 0; })
        | std::views::transform([](int value) { return value * value; });

    bool first = true;
    for (const int value : squares) {
        std::cout << (first ? "" : " ") << value;
        first = false;
    }
    std::cout << '\n';
}
```

View 通常不拥有底层数据，必须保证源范围生命周期足够长。惰性求值意味着转换可能在每次迭代时重复执行；需要稳定结果或多次遍历时应考虑物化到容器。

## Range、迭代器和哨兵

Ranges 把“可以取得 begin/end”建模为 Concept。结束哨兵不必与迭代器同类型，这让以零字符、长度条件或无限序列结束的范围更自然。算法通过 Concept 明确要求输入范围、前向范围、随机访问范围等能力。

Ranges 算法通常返回带信息的结果类型或安全迭代器，并使用投影参数从元素中选取比较字段。它们仍是编译期泛型算法，不建立运行期集合层次。

## View 的典型表示

过滤 View 通常保存底层 View 和谓词，迭代器递增时跳过不满足元素；转换 View 保存底层 View 和转换函数，解引用时调用转换。组合管道构造一组很小的适配器对象，不会预先创建中间容器。

惰性带来零中间分配和早停优势，也意味着副作用函数可能被多次调用，调试时看到的元素并未缓存。某些 View 只满足单遍输入范围，重复遍历不是合法假设。

## 所有权与 `borrowed_range`

从左值容器建立 View 通常保存引用；容器销毁或重分配会使 View/迭代器失效。Ranges 用 `borrowed_range` 描述临时范围销毁后迭代器是否仍安全，并以 `dangling` 返回类型阻止部分误用，但它不能捕获所有跨作用域悬空。

管道右侧适配器常保存谓词副本。捕获引用的 Lambda 会把生命周期问题带入整条管道，异步保存 View 时必须特别谨慎。

## 性能与优化

模板组合让编译器有机会内联谓词和转换、融合循环。性能仍受分支预测、函数对象大小、重复计算和缓存访问影响。复杂 View 链不保证比手写循环更快，热路径应测量生成代码和真实数据。

## 示例解析与实践

示例先惰性过滤偶数，再在解引用时平方，最终只遍历一次源容器。设计管道时标记所有者、确认遍历类别、让转换保持纯净；当结果需要长期保存、排序、随机访问或反复使用时，及时物化到容器。

## 权威资料

- [P0896R4：Ranges](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0896r4.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
