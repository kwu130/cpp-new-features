# mdspan：给连续存储加上多维坐标

阅读前建议先了解：[span 与生命周期](../cpp20/span.md)、[多参数下标](language-improvements.md#多参数-operator二维访问不必绕到-operator)。本篇介绍的新增能力属于 C++23。

## 问题：一维存储，二维访问

矩阵经常存成 vector 或数组，但调用方仍需手写 `data[row * columns + column]`。长度、形状和布局分散在多处，容易把行列弄反。C++23 的 mdspan 把多维形状与下标映射放进一个非拥有视图；它不分配矩阵，也不复制元素。

C++20 span 是一维连续窗口。mdspan 允许多维以及不同映射布局，不能假设每种 mdspan 的逻辑元素都按行连续，也不能默认它是 Range。

## 最小示例：把数组看作两行三列

```cpp example id="cpp23-mdspan" std="c++23" file="main.cpp" kind="single" compilers="all" output="old=6, view=9" requires="__cpp_lib_mdspan>=202207"
#include <array>
#include <cstddef>
#include <iostream>
#include <mdspan>
int main() {
    std::array<int, 6> storage{1, 2, 3, 4, 5, 6};
    std::mdspan<int, std::extents<std::size_t, 2, 3>> matrix(storage.data());
    const int old_value = storage[1 * 3 + 2];
    matrix[1, 2] = 9;
    std::cout << "old=" << old_value << ", view=" << storage[5] << '\n';
}
```

默认 layout_right 使最后一个索引变化最快，本例 [1, 2] 对应 storage[5]。old 记录修改前的 6，view 输出同一存储修改后的 9；两种索引都定位同一个元素，视图没有创建副本。

extents<std::size_t, 2, 3> 把形状写在类型中，不需运行期传长度。动态形状可用 dextents<std::size_t, 2> 并在构造时传 rows、columns；这里的 2 是维数，不是行数。

## 形状、布局与访问策略

| 部分 | 作用 | 常见选择 |
| --- | --- | --- |
| extents | 各维大小 | 静态 extents 或动态 dextents |
| layout | 把坐标映射为偏移 | layout_right、layout_left、layout_stride |
| accessor | 按偏移访问元素 | 默认访问器或自定义策略 |

layout_left 使第一个索引变化最快，适合列优先数据；layout_stride 接收步长，用于外部库已有布局或带间隔的窗口。构造时必须提供足够存储，并满足映射的前置条件。required_span_size 描述映射所需的底层跨度，不总等于各维大小的乘积。

rank()、extent(dimension)、size() 分别回答维数、某维长度和逻辑元素数。布局映射是否唯一、连续覆盖或具有步长由具体映射决定；别把默认示例的线性公式推广到所有映射。

## 生命周期与边界

mdspan 不拥有底层元素。storage 析构或容器重分配后，视图可能悬空；复制 mdspan 只复制访问描述。const mdspan 对象不等于只读元素，限制元素写入要使用 mdspan<const T, ...>。

C++23 的 operator[] 不做通用运行期边界检查，坐标必须合法。mdspan::at、submdspan 与 padded 布局等后续接口不属于本篇的 C++23 范围；不要通过当前工作草案的新成员反推初版接口。

## 场景与性能

适合线性代数、图像、网格及第三方数组的借用适配。拥有数据仍由 vector、array 或专门的资源类型负责；一维遍历 span 更简单。静态尺寸可给优化提供信息，索引计算通常很轻，但不保证向量化或比手写下标更快；存储布局与访问顺序往往更影响缓存行为。

## 权威资料

- [mdspan](https://eel.is/c++draft/mdspan)
- [P0009R18：mdspan](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p0009r18.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/mdspan.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
