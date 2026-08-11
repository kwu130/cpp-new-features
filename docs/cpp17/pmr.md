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

