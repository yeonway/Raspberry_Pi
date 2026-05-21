#include <jni.h>
#include <android/log.h>
#include <algorithm>
#include <clocale>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

#include "llama.h"

#define LOG_TAG "PhoneAiLlama"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

namespace {

struct NativeModel {
    llama_model * model = nullptr;
    const llama_vocab * vocab = nullptr;
    int n_ctx = 1024;
    int n_threads = 4;
};

std::once_flag backend_once;

std::string jstring_to_string(JNIEnv * env, jstring value) {
    if (value == nullptr) {
        return {};
    }
    const char * chars = env->GetStringUTFChars(value, nullptr);
    std::string result(chars == nullptr ? "" : chars);
    if (chars != nullptr) {
        env->ReleaseStringUTFChars(value, chars);
    }
    return result;
}

jstring string_to_jstring(JNIEnv * env, const std::string & value) {
    return env->NewStringUTF(value.c_str());
}

void throw_illegal_state(JNIEnv * env, const std::string & message) {
    jclass clazz = env->FindClass("java/lang/IllegalStateException");
    if (clazz != nullptr) {
        env->ThrowNew(clazz, message.c_str());
    }
}

std::vector<llama_token> tokenize(const llama_vocab * vocab, const std::string & prompt) {
    int n_tokens = -llama_tokenize(vocab, prompt.c_str(), static_cast<int32_t>(prompt.size()), nullptr, 0, true, true);
    if (n_tokens <= 0) {
        throw std::runtime_error("failed to count prompt tokens");
    }

    std::vector<llama_token> tokens(static_cast<size_t>(n_tokens));
    int actual = llama_tokenize(vocab, prompt.c_str(), static_cast<int32_t>(prompt.size()), tokens.data(), n_tokens, true, true);
    if (actual < 0) {
        throw std::runtime_error("failed to tokenize prompt");
    }
    tokens.resize(static_cast<size_t>(actual));
    return tokens;
}

std::string token_to_piece(const llama_vocab * vocab, llama_token token) {
    char buffer[256];
    int n = llama_token_to_piece(vocab, token, buffer, sizeof(buffer), 0, true);
    if (n < 0) {
        std::vector<char> dynamic_buffer(static_cast<size_t>(-n));
        n = llama_token_to_piece(vocab, token, dynamic_buffer.data(), static_cast<int32_t>(dynamic_buffer.size()), 0, true);
        if (n < 0) {
            return {};
        }
        return std::string(dynamic_buffer.data(), static_cast<size_t>(n));
    }
    return std::string(buffer, static_cast<size_t>(n));
}

} // namespace

extern "C" JNIEXPORT jlong JNICALL
Java_com_example_phoneaibridge_ai_LlamaNative_loadModel(
        JNIEnv * env,
        jobject,
        jstring model_path,
        jint n_ctx,
        jint n_threads
) {
    try {
        std::call_once(backend_once, [] {
            std::setlocale(LC_NUMERIC, "C");
            ggml_backend_load_all();
        });

        std::string path = jstring_to_string(env, model_path);
        if (path.empty()) {
            throw std::runtime_error("model path is empty");
        }

        llama_model_params model_params = llama_model_default_params();
        model_params.n_gpu_layers = 0;

        llama_model * model = llama_model_load_from_file(path.c_str(), model_params);
        if (model == nullptr) {
            throw std::runtime_error("unable to load GGUF model: " + path);
        }

        auto * native = new NativeModel();
        native->model = model;
        native->vocab = llama_model_get_vocab(model);
        native->n_ctx = std::max(512, static_cast<int>(n_ctx));
        native->n_threads = std::max(1, static_cast<int>(n_threads));
        LOGI("Loaded model: %s", path.c_str());
        return reinterpret_cast<jlong>(native);
    } catch (const std::exception & e) {
        LOGE("loadModel failed: %s", e.what());
        throw_illegal_state(env, e.what());
        return 0;
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_example_phoneaibridge_ai_LlamaNative_freeModel(JNIEnv *, jobject, jlong handle) {
    auto * native = reinterpret_cast<NativeModel *>(handle);
    if (native == nullptr) {
        return;
    }
    if (native->model != nullptr) {
        llama_model_free(native->model);
    }
    delete native;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_phoneaibridge_ai_LlamaNative_isLoaded(JNIEnv *, jobject, jlong handle) {
    auto * native = reinterpret_cast<NativeModel *>(handle);
    return native != nullptr && native->model != nullptr ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_example_phoneaibridge_ai_LlamaNative_generate(
        JNIEnv * env,
        jobject,
        jlong handle,
        jstring prompt_text,
        jint max_tokens,
        jfloat temperature,
        jint top_k,
        jfloat top_p
) {
    auto * native = reinterpret_cast<NativeModel *>(handle);
    if (native == nullptr || native->model == nullptr || native->vocab == nullptr) {
        throw_illegal_state(env, "model is not loaded");
        return string_to_jstring(env, "");
    }

    llama_context * ctx = nullptr;
    llama_sampler * sampler = nullptr;

    try {
        std::string prompt = jstring_to_string(env, prompt_text);
        std::vector<llama_token> prompt_tokens = tokenize(native->vocab, prompt);
        int n_predict = std::max(1, static_cast<int>(max_tokens));
        int n_ctx = std::max(native->n_ctx, static_cast<int>(prompt_tokens.size()) + n_predict + 8);

        llama_context_params ctx_params = llama_context_default_params();
        ctx_params.n_ctx = static_cast<uint32_t>(std::min(n_ctx, 4096));
        ctx_params.n_batch = static_cast<uint32_t>(std::min<int>(prompt_tokens.size(), 512));
        ctx_params.n_threads = native->n_threads;
        ctx_params.n_threads_batch = native->n_threads;
        ctx_params.no_perf = true;

        ctx = llama_init_from_model(native->model, ctx_params);
        if (ctx == nullptr) {
            throw std::runtime_error("failed to create llama context");
        }

        auto sampler_params = llama_sampler_chain_default_params();
        sampler_params.no_perf = true;
        sampler = llama_sampler_chain_init(sampler_params);
        llama_sampler_chain_add(sampler, llama_sampler_init_top_k(std::max(1, static_cast<int>(top_k))));
        llama_sampler_chain_add(sampler, llama_sampler_init_top_p(std::clamp(static_cast<float>(top_p), 0.05f, 1.0f), 1));
        llama_sampler_chain_add(sampler, llama_sampler_init_temp(std::max(0.0f, static_cast<float>(temperature))));
        llama_sampler_chain_add(sampler, llama_sampler_init_dist(LLAMA_DEFAULT_SEED));

        llama_batch batch = llama_batch_get_one(prompt_tokens.data(), static_cast<int32_t>(prompt_tokens.size()));
        std::string output;
        int n_generated = 0;

        for (int n_pos = 0; n_generated < n_predict;) {
            if (llama_decode(ctx, batch) != 0) {
                throw std::runtime_error("llama_decode failed");
            }
            n_pos += batch.n_tokens;

            llama_token token = llama_sampler_sample(sampler, ctx, -1);
            if (llama_vocab_is_eog(native->vocab, token)) {
                break;
            }

            output += token_to_piece(native->vocab, token);
            batch = llama_batch_get_one(&token, 1);
            n_generated++;
        }

        llama_sampler_free(sampler);
        llama_free(ctx);
        return string_to_jstring(env, output);
    } catch (const std::exception & e) {
        if (sampler != nullptr) {
            llama_sampler_free(sampler);
        }
        if (ctx != nullptr) {
            llama_free(ctx);
        }
        LOGE("generate failed: %s", e.what());
        throw_illegal_state(env, e.what());
        return string_to_jstring(env, "");
    }
}
