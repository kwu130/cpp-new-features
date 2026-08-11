# 移动语义与完美转发

右值引用让类型能够转移资源而非复制资源。`std::move` 表示对象可以被移动，`std::forward` 在转发函数中保留实参原有的值类别。

<!-- example id="cpp11-move-forward" std="c++11" file="main.cpp" kind="single" compilers="all" output="moved 3 values" -->
```cpp
#include <cstddef>
#include <iostream>
#include <utility>
#include <vector>

class Buffer {
public:
    Buffer(std::initializer_list<int> values) : values_(values) {}
    Buffer(Buffer&&) noexcept = default;
    Buffer& operator=(Buffer&&) noexcept = default;
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;
    std::size_t size() const { return values_.size(); }

private:
    std::vector<int> values_;
};

template <typename T, typename... Args>
T make_value(Args&&... args) {
    return T(std::forward<Args>(args)...);
}

int main() {
    Buffer original = make_value<Buffer>(std::initializer_list<int>{1, 2, 3});
    Buffer destination = std::move(original);
    std::cout << "moved " << destination.size() << " values\n";
}
```

## 易错点

`std::move` 本身不移动任何数据，只进行类型转换；真正的转移发生在移动构造或移动赋值中。被移动对象仍然有效，但其值通常未指定，只适合销毁或重新赋值。资源所有者应遵循零法则或五法则。

