// Копируем весь JavaScript код из блока <script>...</script> файла index.html
// из предыдущего ответа (где был улучшенный дизайн плеера) сюда.
// Пример начала файла:
class MusicPlayer {
    constructor() {
        this.audio = new Audio();
        this.playlist = [];
        this.currentTrackIndex = -1;
        this.isPlaying = false;
        this.isShuffled = false;
        this.repeatMode = 'off'; // 'off', 'all', 'one'
        this.originalPlaylist = [];

        // Иконки Play/Pause (Material Symbols names)
        this.playIconName = 'play_arrow';
        this.pauseIconName = 'pause';
        // ... и так далее, весь JS код ...
    }

    // ... все методы класса MusicPlayer ...

}

// Инициализация плеера
document.addEventListener('DOMContentLoaded', () => {
    const player = new MusicPlayer();
    window.musicPlayer = player; // Опционально: сделать доступным глобально для отладки
});

class MusicPlayer {
    constructor() {
        this.audio = new Audio();
        this.playlist = [];
        this.currentTrackIndex = -1;
        this.isPlaying = false;
        this.isShuffled = false;
        this.repeatMode = 'off'; // 'off', 'all', 'one'
        this.originalPlaylist = [];

        this.playIconName = 'play_arrow';
        this.pauseIconName = 'pause';
        this.lightIconName = 'light_mode';
        this.darkIconName = 'dark_mode';
        this.repeatOffIconName = 'repeat';
        this.repeatAllIconName = 'repeat_on'; // Используем другую стандартную иконку для repeat all
        this.repeatOneIconName = 'repeat_one_on'; // Иконка для repeat one

        this.dom = this.getDOMElements();
        this.loadState(); // Загружаем состояние ДО инициализации темы и плейлиста
        this.initTheme();
        this.loadPlaylist();
        this.setupEventListeners();
        this.applyInitialState(); // Применяем громкость и т.д. ПОСЛЕ инициализации
    }

     getDOMElements() {
          return {
              coverImage: document.getElementById('cover-image'),
              trackTitle: document.getElementById('track-title'),
              trackArtist: document.getElementById('track-artist'),
              playPauseBtn: document.querySelector('.play-pause'),
              playPauseIcon: document.getElementById('play-pause-icon'),
              prevBtn: document.querySelector('.previous'),
              nextBtn: document.querySelector('.next'),
              shuffleBtn: document.getElementById('shuffle-btn'),
              repeatBtn: document.getElementById('repeat-btn'),
              repeatIcon: document.getElementById('repeat-icon'),
              progressBar: document.querySelector('.progress-bar'),
              progressContainer: document.querySelector('.progress'),
              currentTimeEl: document.getElementById('current-time'),
              durationEl: document.getElementById('duration'),
              playlistContainer: document.getElementById('playlist'),
              playlistErrorEl: document.getElementById('playlist-error'),
              themeToggleBtn: document.getElementById('theme-toggle'),
              themeIcon: document.getElementById('theme-icon'),
              volumeSlider: document.getElementById('volume-slider'),
              volumeDownBtn: document.querySelector('.volume-down'),
              volumeUpBtn: document.querySelector('.volume-up'),
              searchInput: document.getElementById('search-input'),
          };
     }

      // --- State Handling (localStorage) ---
      loadState() {
          this.currentTrackIndex = parseInt(localStorage.getItem('playerTrackIndex') || '-1', 10);
          this.audio.currentTime = parseFloat(localStorage.getItem('playerCurrentTime') || '0');
          this.audio.volume = parseFloat(localStorage.getItem('playerVolume') || '1');
          this.isShuffled = localStorage.getItem('playerIsShuffled') === 'true';
          this.repeatMode = localStorage.getItem('playerRepeatMode') || 'off';
          // Тема загружается в initTheme
      }

      saveState() {
          localStorage.setItem('playerTrackIndex', this.currentTrackIndex.toString());
          localStorage.setItem('playerCurrentTime', this.audio.currentTime.toString());
          localStorage.setItem('playerVolume', this.audio.volume.toString());
          localStorage.setItem('playerIsShuffled', this.isShuffled.toString());
          localStorage.setItem('playerRepeatMode', this.repeatMode);
      }

      applyInitialState() {
           // Применяем загруженное состояние к UI
           this.dom.volumeSlider.value = this.audio.volume;
           this.updateShuffleButtonState();
           this.updateRepeatButtonState();
           // Индекс трека применится при загрузке плейлиста
      }
     // --- End State Handling ---

     // --- Theme Handling ---
     initTheme() {
         const savedTheme = localStorage.getItem('playerTheme') || 'light';
         document.body.classList.toggle('dark-theme', savedTheme === 'dark');
         this.updateThemeIcon(savedTheme);
     }
     toggleTheme() { /* ... (как в пред. ответе) ... */
         const isDark = document.body.classList.toggle('dark-theme');
         const newTheme = isDark ? 'dark' : 'light';
         localStorage.setItem('playerTheme', newTheme);
         this.updateThemeIcon(newTheme);
     }
     updateThemeIcon(theme) { /* ... (как в пред. ответе) ... */
         this.dom.themeIcon.textContent = theme === 'dark' ? this.lightIconName : this.darkIconName;
     }
     // --- End Theme Handling ---


    displayPlaylistError(message) { /* ... (как в пред. ответе) ... */
         this.dom.playlistContainer.innerHTML = '';
         this.dom.playlistErrorEl.textContent = message;
         this.dom.playlistErrorEl.style.display = 'block';
    }

    loadPlaylist() { /* ... (как в пред. ответе, но вызывает updateTrackInfo для сохраненного индекса) ... */
         this.dom.playlistContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">Загрузка плейлиста...</div>';
        fetch('playlist.json')
            .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
            .then(data => {
                if (!data || !data.tracks || data.tracks.length === 0) { this.displayPlaylistError('Ошибка: Плейлист пуст или не найден.'); return; }
                this.originalPlaylist = data.tracks; // Сохраняем оригинал
                 // Восстанавливаем порядок, если был шаффл
                 if (this.isShuffled) { this.shufflePlaylist(false); } // false = не перерисовывать сразу
                 else { this.playlist = [...this.originalPlaylist]; }

                this.dom.playlistErrorEl.style.display = 'none';
                this.renderPlaylist(); // Рендерим плейлист

                // Устанавливаем инфо для сохраненного трека, если он валиден
                if (this.currentTrackIndex >= 0 && this.currentTrackIndex < this.playlist.length) {
                      this.updateTrackInfo(this.currentTrackIndex);
                      // Устанавливаем src, но не играем, чтобы восстановить позицию
                      this.audio.src = this.playlist[this.currentTrackIndex].src;
                      // Установка currentTime сработает только после 'loadedmetadata' или 'canplay'
                       this.audio.addEventListener('canplay', () => {
                           // Устанавливаем сохраненное время ТОЛЬКО один раз при первой загрузке
                           if (this.audio.readyState >= 2) { // Убедимся что метаданные есть
                                const savedTime = parseFloat(localStorage.getItem('playerCurrentTime') || '0');
                                // Небольшой хак: seek может быть неточным, если делать это слишком рано
                                 setTimeout(() => { this.audio.currentTime = savedTime; this.updateProgress(); }, 100);
                           }
                       }, { once: true }); // Выполнится только один раз
                 } else if (this.playlist.length > 0) {
                      this.updateTrackInfo(0); // Показываем инфо первого трека, если индекс некорректный
                 }
            })
            .catch(error => { console.error('Ошибка:', error); this.displayPlaylistError(`Ошибка: ${error.message}`); });
    }

    setupEventListeners() {
        this.dom.playPauseBtn.addEventListener('click', () => this.togglePlay());
        this.dom.prevBtn.addEventListener('click', () => this.playPrevious());
        this.dom.nextBtn.addEventListener('click', () => this.playNext());
        this.dom.shuffleBtn.addEventListener('click', () => this.toggleShuffle());
        this.dom.repeatBtn.addEventListener('click', () => this.toggleRepeat());
        this.dom.themeToggleBtn.addEventListener('click', () => this.toggleTheme());
        this.dom.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
         this.dom.volumeDownBtn.addEventListener('click', () => this.changeVolume(-0.1));
         this.dom.volumeUpBtn.addEventListener('click', () => this.changeVolume(0.1));
         this.dom.searchInput.addEventListener('input', (e) => this.filterPlaylist(e.target.value));


        this.dom.progressContainer.addEventListener('click', (e) => { /* ... (как в пред. ответе) ... */
            if (!this.audio.duration) return;
             const rect = this.dom.progressContainer.getBoundingClientRect();
             const offsetX = e.clientX - rect.left;
             const percent = Math.max(0, Math.min(1, offsetX / this.dom.progressContainer.offsetWidth));
             this.audio.currentTime = percent * this.audio.duration;
             this.updateProgress();
        });

        // Аудио события
        this.audio.addEventListener('timeupdate', () => { this.updateProgress(); this.saveState(); }); // Сохраняем позицию
        this.audio.addEventListener('ended', () => this.handleTrackEnd()); // Используем отдельный обработчик
        this.audio.addEventListener('loadedmetadata', () => { if(isFinite(this.audio.duration)) this.dom.durationEl.textContent = this.formatTime(this.audio.duration); });
        this.audio.addEventListener('volumechange', () => { this.dom.volumeSlider.value = this.audio.volume; this.saveState(); }); // Сохраняем громкость
        this.audio.addEventListener('play', () => { this.isPlaying = true; this.updatePlayPauseIcon(); this.highlightCurrentTrack(); }); // Обновляем статус при старте
        this.audio.addEventListener('pause', () => { this.isPlaying = false; this.updatePlayPauseIcon(); this.saveState(); }); // Сохраняем при паузе (включая конец трека)
        this.audio.addEventListener('error', (e) => { /* ... (как в пред. ответе) ... */
              console.error("Ошибка аудио:", this.audio.error);
              const trackSrc = this.playlist[this.currentTrackIndex]?.src || "N/A";
              this.dom.trackTitle.textContent = "Ошибка загрузки";
              this.dom.trackArtist.textContent = `Файл: ${trackSrc}`;
              setTimeout(() => { if (this.isPlaying) this.playNext(); }, 1500);
         });


        // Горячие клавиши
        document.addEventListener('keydown', (e) => { /* ... (как в пред. ответе) ... */
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (e.key === ' ') { e.preventDefault(); this.togglePlay(); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); this.playPrevious(); }
            else if (e.key === 'ArrowRight') { e.preventDefault(); this.playNext(); }
            // Добавить M для mute/unmute, стрелки вверх/вниз для громкости и т.д.
        });
    }

     handleTrackEnd() {
         if (this.repeatMode === 'one') {
              this.audio.currentTime = 0;
              this.play();
         } else if (this.repeatMode === 'all' || this.currentTrackIndex < this.playlist.length - 1) {
              // Переходим к следующему если включен повтор всего или это не последний трек
              this.playNext();
         } else {
              // Дошли до конца, повтор выключен - останавливаемся
              this.isPlaying = false;
              this.updatePlayPauseIcon();
              this.audio.currentTime = 0; // Сброс времени
              this.updateProgress();
              // Можно перейти к первому треку, но не играть:
              // this.currentTrackIndex = 0;
              // this.updateTrackInfo(this.currentTrackIndex);
              // this.highlightCurrentTrack();
         }
     }

    renderPlaylist() {
        const fragment = document.createDocumentFragment();
        this.dom.playlistContainer.innerHTML = '';
        if (this.dom.playlistErrorEl.style.display === 'block') return;
        const searchTerm = this.dom.searchInput.value.toLowerCase().trim(); // Для фильтрации

        this.playlist.forEach((track, index) => {
            const item = document.createElement('div');
            item.className = 'playlist-item';
            item.dataset.index = index;

             // Логика фильтрации
             const titleLower = track.title.toLowerCase();
             const artistLower = track.artist.toLowerCase();
             const isVisible = !searchTerm || titleLower.includes(searchTerm) || artistLower.includes(searchTerm);
             if (!isVisible) {
                  item.classList.add('hidden'); // Скрываем, если не соответствует поиску
             }

             const durationStr = track.duration ? this.formatTime(track.duration) : '--:--';

            item.innerHTML = `
                 <div class="playlist-item-info">
                     <div class="title" title="${track.title}">${track.title}</div>
                     <div class="artist" title="${track.artist}">${track.artist}</div>
                 </div>
                 <div class="duration">${durationStr}</div>
            `;
            item.addEventListener('click', () => { /* ... (как в пред. ответе) ... */
                 if (this.currentTrackIndex !== index) { this.currentTrackIndex = index; this.loadAndPlay(); }
                 else if (!this.isPlaying) { this.play(); }
                 else { this.pause(); }
            });
            fragment.appendChild(item);
        });
         this.dom.playlistContainer.appendChild(fragment);
         this.highlightCurrentTrack();
    }

     highlightCurrentTrack() { /* ... (как в пред. ответе) ... */
          this.dom.playlistContainer.querySelectorAll('.playlist-item.active').forEach(el => el.classList.remove('active'));
          if (this.currentTrackIndex >= 0 && this.currentTrackIndex < this.playlist.length) {
               const activeItem = this.dom.playlistContainer.querySelector(`.playlist-item[data-index="${this.currentTrackIndex}"]`);
               if (activeItem) {
                   activeItem.classList.add('active');
                   const containerRect = this.dom.playlistContainer.getBoundingClientRect();
                   const itemRect = activeItem.getBoundingClientRect();
                   if (itemRect.top < containerRect.top || itemRect.bottom > containerRect.bottom) {
                        activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                   }
               }
          }
     }

     updateTrackInfo(index) { /* ... (как в пред. ответе) ... */
          if (index < 0 || index >= this.playlist.length) {
               this.dom.trackTitle.textContent = 'Выберите трек'; this.dom.trackArtist.textContent = '-';
               this.dom.coverImage.classList.add('hidden'); this.dom.coverImage.src = ''; return;
          };
          const track = this.playlist[index];
          this.dom.trackTitle.textContent = track.title; this.dom.trackTitle.title = track.title;
          this.dom.trackArtist.textContent = track.artist; this.dom.trackArtist.title = track.artist;
          if (track.cover) {
              this.dom.coverImage.classList.add('hidden'); const img = new Image();
              img.onload = () => { this.dom.coverImage.src = track.cover; this.dom.coverImage.classList.remove('hidden'); };
              img.onerror = () => { this.dom.coverImage.classList.add('hidden'); this.dom.coverImage.src = ''; }
              img.src = track.cover;
         } else { this.dom.coverImage.classList.add('hidden'); this.dom.coverImage.src = ''; }
         // Обновляем длительность сразу, если она есть в данных
         if (track.duration) { this.dom.durationEl.textContent = this.formatTime(track.duration); }
         else { this.dom.durationEl.textContent = '0:00'; } // Или если длительности нет в JSON
     }

    loadAndPlay() { /* ... (как в пред. ответе, но сохраняет состояние) ... */
         if (this.currentTrackIndex < 0 || this.currentTrackIndex >= this.playlist.length) return;
        const track = this.playlist[this.currentTrackIndex];
         if (!track) return; // Доп. проверка
        this.audio.src = track.src;
         this.updateTrackInfo(this.currentTrackIndex);
         this.highlightCurrentTrack();
        const playPromise = this.audio.play();
        if (playPromise !== undefined) {
            playPromise.then(_ => { this.isPlaying = true; this.updatePlayPauseIcon(); this.saveState(); }) // Сохраняем при начале игры
                   .catch(error => { console.warn("Ошибка автовоспроизведения:", error); this.isPlaying = false; this.updatePlayPauseIcon(); });
        } else { this.isPlaying = true; this.updatePlayPauseIcon(); this.saveState(); }
    }

    togglePlay() { /* ... (как в пред. ответе) ... */
        if (this.playlist.length === 0) return;
        if (this.currentTrackIndex === -1) { this.currentTrackIndex = 0; this.loadAndPlay(); }
        else if (this.isPlaying) { this.pause(); } else { this.play(); }
    }
    play() { /* ... (как в пред. ответе) ... */
        if (!this.audio.src && this.playlist.length > 0) { this.currentTrackIndex = Math.max(0, this.currentTrackIndex); this.loadAndPlay(); return; }
        if(this.audio.src) { this.audio.play().then(() => { this.isPlaying = true; this.updatePlayPauseIcon(); this.highlightCurrentTrack(); }).catch(e => console.error("Ошибка play():", e)); }
    }
    pause() { /* ... (как в пред. ответе) ... */
        this.audio.pause(); this.isPlaying = false; this.updatePlayPauseIcon();
        // Save state on pause too, because timeupdate might not fire exactly at the end
        this.saveState();
    }

    updatePlayPauseIcon() { /* ... (как в пред. ответе) ... */
        this.dom.playPauseIcon.textContent = this.isPlaying ? this.pauseIconName : this.playIconName;
    }
    playNext() { /* ... (как в пред. ответе) ... */
        if (this.playlist.length === 0) return;
        this.currentTrackIndex = (this.currentTrackIndex + 1) % this.playlist.length;
        this.loadAndPlay();
    }
    playPrevious() { /* ... (как в пред. ответе) ... */
         if (this.playlist.length === 0) return; let newIndex;
         if (this.audio.currentTime < 3 && this.currentTrackIndex !== 0) { newIndex = this.currentTrackIndex - 1; }
         else if (this.audio.currentTime < 3 && this.currentTrackIndex === 0) { newIndex = this.playlist.length - 1; }
         else { this.audio.currentTime = 0; if (!this.isPlaying) this.play(); return; }
         this.currentTrackIndex = newIndex; this.loadAndPlay();
    }

    updateProgress() { /* ... (как в пред. ответе) ... */
        if (this.audio.duration && isFinite(this.audio.duration)) {
            const progress = (this.audio.currentTime / this.audio.duration) * 100;
            this.dom.progressBar.style.width = `${progress}%`;
            this.dom.currentTimeEl.textContent = this.formatTime(this.audio.currentTime);
            if (this.dom.durationEl.textContent !== this.formatTime(this.audio.duration)) { this.dom.durationEl.textContent = this.formatTime(this.audio.duration); }
        } else { this.dom.progressBar.style.width = '0%'; this.dom.currentTimeEl.textContent = '0:00'; }
    }
    formatTime(seconds) { /* ... (как в пред. ответе) ... */
         if (isNaN(seconds) || !isFinite(seconds)) return "0:00";
        const minutes = Math.floor(seconds / 60); const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    // --- Shuffle Logic ---
    toggleShuffle() {
        this.isShuffled = !this.isShuffled;
        this.updateShuffleButtonState(); // Обновляем вид кнопки
         this.shufflePlaylist(); // Перемешиваем или восстанавливаем
         this.saveState(); // Сохраняем состояние шаффла
    }

     updateShuffleButtonState() {
         this.dom.shuffleBtn.classList.toggle('active', this.isShuffled);
     }

     shufflePlaylist(render = true) { // Добавлен флаг для рендеринга
         const currentTrackSrc = this.playlist[this.currentTrackIndex]?.src;
         if (this.isShuffled) {
             let shuffled = [...this.originalPlaylist];
             for (let i = shuffled.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]; }
             this.playlist = shuffled;
         } else {
             this.playlist = [...this.originalPlaylist];
         }
         this.currentTrackIndex = this.playlist.findIndex(track => track.src === currentTrackSrc);
         if (this.currentTrackIndex === -1 && this.playlist.length > 0) { this.currentTrackIndex = 0; }
         if (render) this.renderPlaylist(); // Перерисовываем только если нужно
     }
     // --- End Shuffle ---

     // --- Repeat Logic ---
     toggleRepeat() {
          if (this.repeatMode === 'off') this.repeatMode = 'all';
          else if (this.repeatMode === 'all') this.repeatMode = 'one';
          else this.repeatMode = 'off';
          this.updateRepeatButtonState(); // Обновляем вид кнопки
          this.saveState(); // Сохраняем состояние
     }

     updateRepeatButtonState() {
          let iconName = this.repeatOffIconName;
          let title = 'Повтор выключен';
          if (this.repeatMode === 'all') {
               iconName = this.repeatAllIconName;
               this.dom.repeatBtn.classList.add('active');
               title = 'Повтор плейлиста';
          } else if (this.repeatMode === 'one') {
               iconName = this.repeatOneIconName;
               this.dom.repeatBtn.classList.add('active'); // Оставляем активным
               title = 'Повтор трека';
          } else {
               this.dom.repeatBtn.classList.remove('active');
          }
          this.dom.repeatIcon.textContent = iconName;
          this.dom.repeatBtn.title = title; // Обновляем title кнопки
     }
     // --- End Repeat ---

     // --- Volume Logic ---
     setVolume(value) {
          this.audio.volume = parseFloat(value);
           // Обновляем иконку mute/unmute если нужно будет добавить
     }
     changeVolume(delta) {
          let newVolume = Math.max(0, Math.min(1, this.audio.volume + delta));
          this.setVolume(newVolume);
          this.dom.volumeSlider.value = newVolume; // Обновляем слайдер
     }
     // --- End Volume ---

     // --- Playlist Filter ---
     filterPlaylist(term) {
          const lowerTerm = term.toLowerCase().trim();
          const items = this.dom.playlistContainer.querySelectorAll('.playlist-item');
          let visibleCount = 0;
          items.forEach((item, index) => {
               const track = this.playlist[item.dataset.index]; // Получаем трек по data-index
               if (!track) return; // Пропуск если трека нет
               const titleLower = track.title.toLowerCase();
               const artistLower = track.artist.toLowerCase();
               const isVisible = !lowerTerm || titleLower.includes(lowerTerm) || artistLower.includes(lowerTerm);
               item.classList.toggle('hidden', !isVisible);
               if(isVisible) visibleCount++;
          });
          // Можно добавить сообщение "Ничего не найдено"
          // console.log(`Найдено ${visibleCount} треков по запросу "${term}"`);
     }
     // --- End Filter ---

}

document.addEventListener('DOMContentLoaded', () => { const player = new MusicPlayer(); });