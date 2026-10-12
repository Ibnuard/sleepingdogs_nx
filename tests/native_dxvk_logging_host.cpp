/* SPDX-License-Identifier: MIT; exercise actual queue and overlaid log functions. */
#include "native_log_queue.h"
#include "com_progress.h"
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <cstdarg>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

static int fx_debug_live=1,sd_com_enabled=1;
static FILE* fx_debug_file;
static pthread_mutex_t fx_debug_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fx_debug_file_lock=PTHREAD_MUTEX_INITIALIZER;
static char fx_debug_lines[21][120];static unsigned fx_debug_total;
static unsigned crash_notes;
static void wine_nx_f1_crash_note(const char*){++crash_notes;}
#include "runtime_logging.inc"
static std::string captured;
static void collect(const char* data,size_t bytes,void*){captured.append(data,bytes);}
static void drain(){while(sd_native_log_drain(collect,nullptr)){};}
static std::mutex sink_mutex;static std::condition_variable sink_cv;
static bool sink_entered,sink_release,producer_done;
static void blocked_sink(const char*,size_t,void*) {
    std::unique_lock<std::mutex> lock(sink_mutex);sink_entered=true;sink_cv.notify_all();
    sink_cv.wait(lock,[]{return sink_release;});
}
int main() {
    fx_debug_file=tmpfile();assert(fx_debug_file);
    log_line("native %d",1);assert(ftell(fx_debug_file)==0);
    assert(sd_native_log_drain(sd_native_log_write,nullptr)==1);
    assert(ftell(fx_debug_file)==9);
    sd_com_enabled=0;log_line("legacy");assert(ftell(fx_debug_file)==16);
    sd_com_enabled=1;log_line("[BIND] ignored");assert(!sd_native_log_count);
    log_line("[FAIL] retained");assert(crash_notes==1);drain();assert(captured=="[FAIL] retained\n");captured.clear();
    pthread_mutex_lock(&sd_native_log_lock);log_line("busy queue");pthread_mutex_unlock(&sd_native_log_lock);
    drain();assert(captured.find("dropped=1")!=std::string::npos);captured.clear();
    for(unsigned i=0;i<SD_NATIVE_LOG_SLOTS+2;++i)log_line("record %u",i);
    drain();assert(captured.find("dropped=2")!=std::string::npos);
    assert(captured.find("record 511\n")!=std::string::npos&&captured.find("record 512\n")==std::string::npos);
    captured.clear();std::string large(2000,'x');sd_native_log_enqueue(large.c_str());drain();
    assert(captured.size()==SD_NATIVE_LOG_LINE-1&&captured.back()=='\n');captured.clear();
    // A stuck storage sink must not hold the queue or block COM's producer.
    log_line("blocking write");std::thread consumer([]{sd_native_log_drain(blocked_sink,nullptr);});
    {std::unique_lock<std::mutex> lock(sink_mutex);assert(sink_cv.wait_for(lock,std::chrono::seconds(2),[]{return sink_entered;}));}
    std::thread producer([]{log_line("producer still runs");std::lock_guard<std::mutex> lock(sink_mutex);producer_done=true;sink_cv.notify_all();});
    {std::unique_lock<std::mutex> lock(sink_mutex);assert(sink_cv.wait_for(lock,std::chrono::seconds(2),[]{return producer_done;}));sink_release=true;sink_cv.notify_all();}
    producer.join();consumer.join();drain();assert(captured=="producer still runs\n");captured.clear();
    std::vector<std::thread> writers;
    for(unsigned t=0;t<4;++t)writers.emplace_back([t]{for(unsigned i=0;i<64;++i)sd_native_log_enqueue(("thread "+std::to_string(t)+" row "+std::to_string(i)).c_str());});
    for(auto& thread:writers)thread.join();
    // Contention is explicitly lossy; all accepted records must stay whole.
    drain();size_t accepted=0,at=0;
    while(at<captured.size()){auto end=captured.find('\n',at);assert(end!=std::string::npos);auto line=captured.substr(at,end-at);at=end+1;
        if(line.find("thread ")==0){assert(line.find(" row ")!=std::string::npos);++accepted;}
        else assert(line.find("[SD-NDX-LOG] dropped=")==0);}
    assert(accepted>0&&accepted<=256);
    using namespace sd_com_progress;State progress;Snapshot data{};
    progress.sequence.store(1);assert(!progress.read(data));progress.sequence.store(2);
    std::atomic<bool> stop{false};std::atomic<unsigned> reads{0};
    std::thread observer([&]{Snapshot value{};while(!stop){if(progress.read(value)){for(auto field:value)assert(field==value[0]);++reads;}}});
    for(uint64_t i=1;i<=20000;++i){data.fill(i);progress.publish(data);}
    stop=true;observer.join();assert(reads>0&&progress.read(data));for(auto field:data)assert(field==20000);
    fclose(fx_debug_file);
    puts("PASS: native queue, legacy log path, drop/truncation, blocked sink, concurrent producers and coherent nonblocking snapshots");
}
