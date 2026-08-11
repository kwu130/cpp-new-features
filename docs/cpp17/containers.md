# 容器接口增强

关联容器加入节点句柄，可在不复制元素的情况下转移节点；`try_emplace` 和 `insert_or_assign` 更明确地区分“缺失时构造”与“存在时覆盖”。

<!-- example id="cpp17-containers" std="c++17" file="main.cpp" kind="single" compilers="all" output="answer=43" -->
```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> source;
    source.try_emplace("answer", 42);

    auto node = source.extract("answer");
    node.mapped() += 1;
    std::map<std::string, int> destination;
    destination.insert(std::move(node));
    destination.insert_or_assign("answer", 43);

    std::cout << "answer=" << destination.at("answer") << '\n';
}
```

节点只能在兼容的容器和分配器条件下转移。`try_emplace` 在键已存在时不会构造映射值，适合构造成本高或不可移动的值。

