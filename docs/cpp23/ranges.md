# Ranges 扩展：收集、并行配对、编号与分块

阅读前建议先了解：[C++20 Ranges](../cpp20/ranges.md)、[结构化绑定](../cpp17/control-flow.md)。本篇介绍的新增能力属于 C++23。

## 先建立 C++20 管道，再学习 C++23 扩展

C++20 已能 filter、transform 和 take，但收集到容器、同时遍历两份数据、带编号遍历或按块处理往往要写额外循环。C++23 添加相应接口；源数据生命周期和惰性求值规则仍然重要。

先用 ranges::to 把有限管道保存下来，再分别学 zip、enumerate 和 chunk。后面的例子不是要求四种操作一起使用。

## ranges::to：把有限范围收集到容器

传统方法遍历并 push_back。to 将构造选择与插入逻辑包装为统一转换接口，不改变结果容器拥有数据的事实。

```cpp example id="cpp23-ranges-to" std="c++23" file="main.cpp" kind="single" compilers="all" output="values=4 16" requires="__cpp_lib_ranges_to_container>=202202"
#include <cassert>
#include <iostream>
#include <ranges>
#include <vector>
int main() {
    const std::vector<int> input{1, 2, 3, 4};
    auto pipeline = input
        | std::views::filter([](int value) { return value % 2 == 0; })
        | std::views::transform([](int value) { return value * value; });
    std::vector<int> old_result;
    for (int value : pipeline) old_result.push_back(value);
    auto result = pipeline | std::ranges::to<std::vector<int>>();
    assert(result == old_result);
    std::cout << "values=" << result[0] << ' ' << result[1] << '\n';
}
```

结果都是 4、16。to 在调用时消费范围；无限范围必须先 take 等限制长度。允许构造的路径取决于目标容器和元素类型；不可复制元素可能需要明确的移动范围，不能默认对左值源进行搬移。

## zip：按位置配对，到最短范围结束

过去用共同索引并检查两份长度。zip 生成 tuple 式元素，让结构化绑定直接取得每对数据。

```cpp example id="cpp23-ranges-zip" std="c++23" file="main.cpp" kind="single" compilers="all" output="pairs=A:10 B:20" requires="__cpp_lib_ranges_zip>=202110"
#include <array>
#include <cassert>
#include <iostream>
#include <ranges>
int main() {
    std::array labels{'A', 'B', 'C'};
    std::array values{10, 20};
    int count = 0;
    std::cout << "pairs=";
    for (auto [label, value] : std::views::zip(labels, values)) {
        std::cout << (count ? " " : "") << label << ':' << value;
        ++count;
    }
    assert(count == 2);
    std::cout << '\n';
}
```

第三个标签没有配对值，遍历结束。zip 不检查“两份业务数据必须一样长”，需要该约束时先检查长度。tuple 中的元素通常仍引用原元素；即使绑定声明写 auto，修改元素也可能影响源。zip_transform 可同时配对并执行转换；adjacent 与 adjacent_transform 组合相邻元素。

## enumerate：得到编号与元素

传统循环自己维护 index。enumerate 产出索引和元素，索引类型来自范围差值类型，不必固定为 size_t。

```cpp example id="cpp23-ranges-enumerate" std="c++23" file="main.cpp" kind="single" compilers="all" output="items=0:4 1:5" requires="__cpp_lib_ranges_enumerate>=202302"
#include <array>
#include <iostream>
#include <ranges>
int main() {
    std::array values{4, 5};
    std::cout << "items=";
    bool first = true;
    for (auto [index, value] : std::views::enumerate(values)) {
        std::cout << (first ? "" : " ") << index << ':' << value;
        first = false;
    }
    std::cout << '\n';
}
```

适合日志编号或算法中同时需要位置与元素的情况；只关心元素时范围循环更简单。编号是当前遍历顺序的位置，不是容器中的稳定对象 ID。

## chunk：连续分块，最后一块可以较短

```cpp example id="cpp23-ranges-chunk" std="c++23" file="main.cpp" kind="single" compilers="all" output="blocks=12|34|5" requires="__cpp_lib_ranges_chunk>=202202"
#include <array>
#include <iostream>
#include <ranges>
int main() {
    std::array values{1, 2, 3, 4, 5};
    bool first = true;
    std::cout << "blocks=";
    for (auto block : values | std::views::chunk(2)) {
        std::cout << (first ? "" : "|");
        for (int value : block) std::cout << value;
        first = false;
    }
    std::cout << '\n';
}
```

chunk 每块至多 2 个元素，最后一块只有 5。块大小必须为正数。slide 产生固定大小、互相重叠的窗口，要求不同于 chunk；chunk_by 按相邻元素谓词的关系分组，不能把它误解为对任意元素做全局分组。

## 其他扩展与生命周期

join_with 在子范围之间插入分隔范围，repeat 产生重复值，cartesian_product 组合笛卡尔积，as_rvalue 把元素访问转换为可供移动的形式。ranges 算法还增加 contains、contains_subrange、starts_with、ends_with、find_last 等。它们各有能力约束和独立测试宏，支持 zip 不代表已经支持全部新 View。

本篇的源数组和 vector 都活到遍历结束。不要返回引用局部源的管道，或把 input_range 的单次遍历当成可重复遍历。物化后的容器通常拥有元素，但若元素本身是指针、引用包装或视图，指向的数据仍可能悬空。延迟操作是否缓存 begin、元素引用是否失效，继续按具体 View 与源容器的规则判断。

C++20 的 owning_view 等回溯缺陷修正不是 C++23 才首次提供的接口。C++26 的 ranges::cache_latest 等后续能力不混入本篇。

## 权威资料

- [范围转换](https://eel.is/c++draft/range.utility.conv)、[zip](https://eel.is/c++draft/range.zip)
- [enumerate](https://eel.is/c++draft/range.enumerate)、[chunk](https://eel.is/c++draft/range.chunk)
- [P1206R7：Ranges 转换与容器构造](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p1206r7.pdf)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/ranges.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
