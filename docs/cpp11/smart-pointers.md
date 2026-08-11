# 智能指针

智能指针把资源生命周期绑定到对象生命周期。`unique_ptr` 表示独占所有权，`shared_ptr` 表示共享所有权，`weak_ptr` 用于非拥有观察并打破共享环。

<!-- example id="cpp11-smart-pointers" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42 owners=2" -->
```cpp
#include <iostream>
#include <memory>

int main() {
    std::unique_ptr<int> unique(new int(42));
    std::shared_ptr<int> shared = std::move(unique);
    std::weak_ptr<int> observer = shared;

    if (std::shared_ptr<int> locked = observer.lock()) {
        std::cout << "value=" << *locked << " owners=" << locked.use_count() << '\n';
    }
}
```

默认优先使用 `unique_ptr`，只有确有共同生命周期时才使用 `shared_ptr`。不要用同一个裸指针分别构造多个 `shared_ptr`。C++11 尚无 `make_unique`，它在 C++14 中加入；创建共享对象则应优先使用 `make_shared`。

