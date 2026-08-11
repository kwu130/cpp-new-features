# 多态内存资源 `pmr`

`std::pmr` 把分配策略从容器类型中分离。相同容器类型可在运行期选择单调缓冲区、池资源或自定义资源。

<!-- example id="cpp17-pmr" std="c++17" file="main.cpp" kind="single" compilers="all" output="alpha beta" -->
```cpp
#include <array>
#include <cstddef>
#include <iostream>
#include <memory_resource>
#include <string>
#include <vector>

int main() {
    std::array<std::byte, 1024> storage{};
    std::pmr::monotonic_buffer_resource resource(storage.data(), storage.size());
    std::pmr::vector<std::pmr::string> words(&resource);
    words.emplace_back("alpha");
    words.emplace_back("beta");
    std::cout << words[0] << ' ' << words[1] << '\n';
}
```

单调资源只在资源整体释放时回收内存，适合批量、阶段性生命周期。使用资源的对象不能比资源活得更久；跨资源移动容器也可能退化为逐元素移动。

## 分配器问题与 `memory_resource`

传统分配器类型参与容器类型，换一种策略会产生不同容器类型并传播模板参数。PMR 容器使用 `polymorphic_allocator`，内部只保存指向 `memory_resource` 的运行期接口，因此相同 `pmr::vector<T>` 可以连接不同资源。

`memory_resource` 通过虚函数执行分配、释放和相等性比较。相较编译期分配器多一次间接调用，但通常分配本身成本更高；真正收益来自批量策略、减少系统分配和改善局部性。

## 单调缓冲区资源

`monotonic_buffer_resource` 从初始缓冲区顺序切块，单次 `deallocate` 通常不回收，销毁资源时一次释放全部上游块。分配接近指针递增，非常适合解析请求、构建 AST、帧临时数据等同生命周期对象图。

初始缓冲区耗尽后默认向上游资源申请更多块。若业务要求严格禁止堆分配，可把 `null_memory_resource()` 作为上游，并处理 `bad_alloc`。

## 传播与嵌套对象

PMR 容器构造元素时会通过 uses-allocator 机制把资源传播给支持它的嵌套 PMR 类型。示例的 `pmr::string` 因此使用同一单调资源。普通 `std::string` 不会自动改用该资源。

资源不是拥有型智能指针。容器只保存裸资源指针，资源必须比所有分配自它的对象活得更久。把局部资源构造的容器返回给调用方会产生悬空分配器。

## 相等性和移动成本

两个资源若不报告相等，容器跨资源移动赋值可能必须逐元素移动到目标资源，不能只交换内部指针。性能设计应把资源边界与对象生命周期边界对齐。

## 工程实践

先用分析工具确认分配是瓶颈，再选择资源；记录资源所有者和销毁顺序；测试缓冲区耗尽路径；不要把 PMR 当作通用“更快容器”，它优化的是特定生命周期和分配模式。

## 权威资料

- [P0220R1：多态内存资源](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2016/p0220r1.html)
- [CPP17 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0636r3.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
